package io.saksk.ti.web.security.support;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.time.Duration;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * A test-only TCP gate that can make a stable loopback port genuinely refuse connections.
 *
 * <p>The gate closes both its listener and every accepted socket on interruption. Reopening binds
 * the same port and forwards new connections to the real Redis endpoint. This exercises Lettuce's
 * network recovery path without mocking Redis commands or replacing the production limiter.</p>
 */
public final class Phase4cRedisNetworkGate implements AutoCloseable {

    private static final InetAddress LOOPBACK = loopback();
    private static final Duration UPSTREAM_CONNECT_TIMEOUT = Duration.ofSeconds(2);

    private final int listenPort;
    private final InetSocketAddress upstreamAddress;
    private final ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
    private final Set<Connection> connections = ConcurrentHashMap.newKeySet();
    private final AtomicBoolean closed = new AtomicBoolean();

    private volatile ServerSocket listener;

    public Phase4cRedisNetworkGate(int listenPort, String upstreamHost, int upstreamPort) {
        if (listenPort < 1 || listenPort > 65_535) {
            throw new IllegalArgumentException("listenPort must be 1..65535");
        }
        this.listenPort = listenPort;
        this.upstreamAddress = new InetSocketAddress(upstreamHost, upstreamPort);
    }

    /** Returns a loopback port whose listener has been closed, so initial connects are refused. */
    public static int reserveRefusedPort() throws IOException {
        try (ServerSocket socket = new ServerSocket(0, 1, LOOPBACK)) {
            return socket.getLocalPort();
        }
    }

    public int listenPort() {
        return listenPort;
    }

    /** Starts forwarding on the stable port. Calling this while already open is harmless. */
    public synchronized void open() throws IOException {
        ensureNotClosed();
        if (listener != null && !listener.isClosed()) {
            return;
        }
        ServerSocket next = new ServerSocket();
        next.setReuseAddress(true);
        next.bind(new InetSocketAddress(LOOPBACK, listenPort), 64);
        listener = next;
        executor.submit(() -> accept(next));
    }

    /**
     * Drops active traffic and removes the listener. New connects then receive connection refused
     * until {@link #open()} rebinds the same port.
     */
    public synchronized void refuseConnections() {
        closeListener();
        closeConnections();
    }

    public boolean isOpen() {
        ServerSocket current = listener;
        return current != null && !current.isClosed();
    }

    @Override
    public void close() {
        synchronized (this) {
            if (!closed.compareAndSet(false, true)) {
                return;
            }
            closeListener();
            closeConnections();
        }
        executor.close();
    }

    private void accept(ServerSocket expectedListener) {
        while (!closed.get() && expectedListener == listener && !expectedListener.isClosed()) {
            try {
                Socket client = expectedListener.accept();
                executor.submit(() -> connectAndForward(expectedListener, client));
            } catch (SocketException exception) {
                if (!expectedListener.isClosed() && !closed.get()) {
                    throw new IllegalStateException("Redis network gate listener failed", exception);
                }
                return;
            } catch (IOException exception) {
                if (!expectedListener.isClosed() && !closed.get()) {
                    throw new IllegalStateException("Redis network gate accept failed", exception);
                }
                return;
            }
        }
    }

    private void connectAndForward(ServerSocket expectedListener, Socket client) {
        Socket upstream = new Socket();
        Connection connection = new Connection(client, upstream);
        try {
            configure(client);
            upstream.connect(
                    upstreamAddress,
                    Math.toIntExact(UPSTREAM_CONNECT_TIMEOUT.toMillis()));
            configure(upstream);
            synchronized (this) {
                if (expectedListener != listener || expectedListener.isClosed() || closed.get()) {
                    return;
                }
                connections.add(connection);
            }
            executor.submit(() -> copy(connection, client, upstream));
            copy(connection, upstream, client);
        } catch (IOException ignored) {
            // Refusal and mid-stream closure are the fault conditions this support class creates.
        } finally {
            connection.close();
            connections.remove(connection);
        }
    }

    private void copy(Connection connection, Socket source, Socket destination) {
        try {
            InputStream input = source.getInputStream();
            OutputStream output = destination.getOutputStream();
            input.transferTo(output);
        } catch (IOException ignored) {
            // The peer task or refuseConnections() deliberately closes both sides.
        } finally {
            connection.close();
            connections.remove(connection);
        }
    }

    private static void configure(Socket socket) throws SocketException {
        socket.setTcpNoDelay(true);
        socket.setKeepAlive(true);
    }

    private void closeListener() {
        ServerSocket current = listener;
        listener = null;
        if (current != null) {
            try {
                current.close();
            } catch (IOException ignored) {
                // Closing the listener is best effort; it is already unusable after this point.
            }
        }
    }

    private void closeConnections() {
        for (Connection connection : connections) {
            connection.close();
        }
        connections.clear();
    }

    private void ensureNotClosed() {
        if (closed.get()) {
            throw new IllegalStateException("Redis network gate is closed");
        }
    }

    private static InetAddress loopback() {
        try {
            return InetAddress.getByName("127.0.0.1");
        } catch (IOException exception) {
            throw new ExceptionInInitializerError(exception);
        }
    }

    private record Connection(Socket client, Socket upstream) {

        private void close() {
            close(client);
            close(upstream);
        }

        private static void close(Socket socket) {
            try {
                socket.close();
            } catch (IOException ignored) {
                // Both forwarding directions race to close the same pair by design.
            }
        }
    }
}
