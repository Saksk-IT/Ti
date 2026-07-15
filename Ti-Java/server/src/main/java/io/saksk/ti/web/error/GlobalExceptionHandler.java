package io.saksk.ti.web.error;

import java.util.List;
import java.util.Locale;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import io.saksk.ti.web.contract.ApiErrorDetail;
import io.saksk.ti.web.contract.ApiErrorEnvelope;
import io.saksk.ti.web.contract.ApiResponses;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger LOGGER = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    ResponseEntity<ApiErrorEnvelope> handleApiException(
            ApiException exception,
            HttpServletRequest request
    ) {
        return response(exception.errorCode(), exception.safeDetails(), request);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiErrorEnvelope> handleMethodArgumentNotValid(
            MethodArgumentNotValidException exception,
            HttpServletRequest request
    ) {
        List<ApiErrorDetail> details = exception.getBindingResult().getFieldErrors().stream()
                .map(this::toSafeDetail)
                .toList();
        return response(ErrorCode.INVALID_REQUEST, details, request);
    }

    @ExceptionHandler({
            ConstraintViolationException.class,
            HandlerMethodValidationException.class,
            HttpMessageNotReadableException.class,
            MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class
    })
    ResponseEntity<ApiErrorEnvelope> handleInvalidRequest(
            Exception exception,
            HttpServletRequest request
    ) {
        return response(ErrorCode.INVALID_REQUEST, List.of(), request);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ApiErrorEnvelope> handleNotFound(
            NoResourceFoundException exception,
            HttpServletRequest request
    ) {
        return response(ErrorCode.RESOURCE_NOT_FOUND, List.of(), request);
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    ResponseEntity<ApiErrorEnvelope> handleMethodNotAllowed(
            HttpRequestMethodNotSupportedException exception,
            HttpServletRequest request
    ) {
        return response(ErrorCode.METHOD_NOT_ALLOWED, List.of(), request);
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    ResponseEntity<ApiErrorEnvelope> handleUnsupportedMediaType(
            HttpMediaTypeNotSupportedException exception,
            HttpServletRequest request
    ) {
        return response(ErrorCode.UNSUPPORTED_MEDIA_TYPE, List.of(), request);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiErrorEnvelope> handleUnexpected(
            Exception exception,
            HttpServletRequest request
    ) {
        LOGGER.error("Unhandled request failure type={}", exception.getClass().getName());
        return response(ErrorCode.INTERNAL_ERROR, List.of(), request);
    }

    private ApiErrorDetail toSafeDetail(FieldError error) {
        String validationCode = error.getCode() == null
                ? "INVALID"
                : error.getCode().toUpperCase(Locale.ROOT);
        return new ApiErrorDetail(error.getField(), validationCode, "字段校验失败");
    }

    private ResponseEntity<ApiErrorEnvelope> response(
            ErrorCode errorCode,
            List<ApiErrorDetail> details,
            HttpServletRequest request
    ) {
        return ResponseEntity
                .status(errorCode.status())
                .body(ApiResponses.error(errorCode, details, request));
    }
}
