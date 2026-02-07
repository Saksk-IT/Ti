---
name: 安全审计
description: 持续安全漏洞扫描，覆盖OWASP Top 10、常见漏洞和不安全模式。在代码审查、部署前或文件变更时使用。扫描SQL注入、XSS、密钥泄露、认证问题。在文件变更、安全相关讨论、部署准备时触发。
allowed-tools: Read, Grep, Bash
---

# Security Auditor Skill

Automatic security vulnerability detection.

## When I Activate

- ✅ Code files modified (especially auth, API, database)
- ✅ User mentions security or vulnerabilities
- ✅ Before deployments or commits
- ✅ Dependency changes
- ✅ Configuration file changes

## What I Scan For

### OWASP Top 10 Patterns

**1. SQL Injection**
```javascript
// CRITICAL: SQL injection
const query = `SELECT * FROM users WHERE id = ${userId}`;

// SECURE: Parameterized query
const query = 'SELECT * FROM users WHERE id = ?';
db.query(query, [userId]);
```

**2. XSS (Cross-Site Scripting)**
```javascript
// CRITICAL: XSS vulnerability
element.innerHTML = userInput;

// SECURE: Use textContent or sanitize
element.textContent = userInput;
// or
element.innerHTML = DOMPurify.sanitize(userInput);
```

**3. Authentication Issues**
```javascript
// CRITICAL: Weak JWT secret
const token = jwt.sign(payload, 'secret123');

// SECURE: Strong secret from environment
const token = jwt.sign(payload, process.env.JWT_SECRET);
```

**4. Sensitive Data Exposure**
```python
# CRITICAL: Exposed password
password = "admin123"

# SECURE: Environment variable
password = os.getenv("DB_PASSWORD")
```

**5. Broken Access Control**
```javascript
// CRITICAL: No authorization check
app.delete('/api/users/:id', (req, res) => {
  User.delete(req.params.id);
});

// SECURE: Authorization check
app.delete('/api/users/:id', auth, checkOwnership, (req, res) => {
  User.delete(req.params.id);
});
```

### Additional Security Checks

- **Insecure Deserialization**
- **Security Misconfiguration**
- **Insufficient Logging**
- **CSRF Protection Missing**
- **CORS Misconfiguration**

## Alert Format

```
🚨 CRITICAL: [Vulnerability type]
📍 Location: file.js:42
🔧 Fix: [Specific remediation]
📖 Reference: [OWASP/CWE link]
```

### Severity Levels

- 🚨 **CRITICAL**: Must fix immediately (exploitable vulnerabilities)
- ⚠️ **HIGH**: Should fix soon (security weaknesses)
- 📋 **MEDIUM**: Consider fixing (potential issues)
- 💡 **LOW**: Best practice improvements

## Real-World Examples

### SQL Injection Detection

```javascript
// You write:
app.get('/users', (req, res) => {
  const sql = `SELECT * FROM users WHERE name = '${req.query.name}'`;
  db.query(sql, (err, results) => res.json(results));
});

// I alert:
🚨 CRITICAL: SQL injection vulnerability (line 2)
📍 File: routes/users.js, Line 2
🔧 Fix: Use parameterized queries
  const sql = 'SELECT * FROM users WHERE name = ?';
  db.query(sql, [req.query.name], ...);
📖 https://owasp.org/www-community/attacks/SQL_Injection
```

### Password Storage

```python
# You write:
def create_user(username, password):
    user = User(username=username, password=password)
    user.save()

# I alert:
🚨 CRITICAL: Storing plain text password (line 2)
📍 File: models.py, Line 2
🔧 Fix: Hash passwords before storing
  from bcrypt import hashpw, gensalt
  hashed = hashpw(password.encode(), gensalt())
  user = User(username=username, password=hashed)
📖 Use bcrypt, scrypt, or argon2 for password hashing
```

### API Key Exposure

```javascript
// You write:
const stripe = require('stripe')('sk_live_abc123...');

// I alert:
🚨 CRITICAL: Hardcoded API key detected (line 1)
📍 File: payment.js, Line 1
🔧 Fix: Use environment variables
  const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
📖 Never commit API keys to version control
```

## Dependency Scanning

I can run security audits on dependencies:

```bash
# Node.js
npm audit

# Python
pip-audit

# Results flagged with severity
```

## Relationship with @code-reviewer Sub-Agent

**Me (Skill):** Quick vulnerability pattern detection
**@code-reviewer (Sub-Agent):** Deep security audit with threat modeling

### Workflow
1. I detect vulnerability pattern
2. I flag: "🚨 SQL injection detected"
3. You want full analysis → Invoke **@code-reviewer** sub-agent
4. Sub-agent provides comprehensive security audit

## Common Vulnerability Patterns

### Authentication
- Weak password policies
- Missing MFA
- Session fixation
- Insecure password storage

### Authorization
- Missing access control
- Privilege escalation
- IDOR (Insecure Direct Object Reference)

### Data Protection
- Unencrypted sensitive data
- Weak encryption algorithms
- Missing HTTPS
- Insecure cookies

### Input Validation
- SQL injection
- Command injection
- XSS
- Path traversal

## Sandboxing Compatibility

**Works without sandboxing:** ✅ Yes
**Works with sandboxing:** ✅ Yes

**Optional: For dependency scanning**
```json
{
  "network": {
    "allowedDomains": [
      "registry.npmjs.org",
      "pypi.org",
      "api.github.com"
    ]
  }
}
```

## Integration with Tools

### With secret-scanner Skill
```
security-auditor: Checks code patterns
secret-scanner: Checks for exposed secrets
Together: Comprehensive security coverage
```

### With /review Command
```bash
/review --scope staged --checks security

# Workflow:
# 1. My automatic security findings
# 2. @code-reviewer sub-agent deep audit
# 3. Comprehensive security report
```

## Customization

Add company-specific security patterns:

```bash
cp -r ~/.claude/skills/security/security-auditor \
      ~/.claude/skills/security/company-security-auditor

# Edit SKILL.md to add:
# - Internal API patterns
# - Company security policies
# - Custom vulnerability checks
```

## Learn More

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Security Best Practices](../../standards/security/)
