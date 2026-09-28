# JWT (JSON Web Token) — Complete Notes for Backend Interviews

> **Audience:** Python / FastAPI developers  
> **Purpose:** Understand JWT from fundamentals to practical implementation and prepare for backend interviews.  
> **Last reviewed:** September 2026

---

## Table of Contents

1. [What is JWT?](#1-what-is-jwt)
2. [Authentication vs. Authorization](#2-authentication-vs-authorization)
3. [Stateful vs. Stateless Authentication](#3-stateful-vs-stateless-authentication)
4. [Structure of a JWT](#4-structure-of-a-jwt)
5. [How JWT Signing and Verification Work](#5-how-jwt-signing-and-verification-work)
6. [HS256 vs. RS256](#6-hs256-vs-rs256)
7. [JWT Authentication Flow](#7-jwt-authentication-flow)
8. [Access Tokens and Refresh Tokens](#8-access-tokens-and-refresh-tokens)
9. [JWT vs. OAuth 2.0 vs. OpenID Connect](#9-jwt-vs-oauth-20-vs-openid-connect)
10. [JWT in FastAPI](#10-jwt-in-fastapi)
11. [JWT Security Best Practices](#11-jwt-security-best-practices)
12. [Limitations and Trade-offs](#12-limitations-and-trade-offs)
13. [Common Misconceptions](#13-common-misconceptions)
14. [Interview Questions and Answers](#14-interview-questions-and-answers)
15. [Quick Revision Cheat Sheet](#15-quick-revision-cheat-sheet)
16. [References](#16-references)

---

## 1. What is JWT?

**JWT (JSON Web Token)** is a compact, URL-safe format for representing a set of claims that can be transferred between parties. A signed JWT lets a recipient verify the token's integrity and the authenticity of its signer.

JWT is commonly used as an **access-token format** in API authentication and authorization systems.

A typical signed JWT looks like this:

```text
xxxxx.yyyyy.zzzzz
```

It has three Base64URL-encoded parts separated by dots:

```text
HEADER.PAYLOAD.SIGNATURE
```

JWT does not inherently require a server-side record for every issued token. A server can validate a signed token using a configured verification key and validate its claims. This is often called **stateless token validation**.

### Why is JWT used?

- It is compact and convenient to transmit in HTTP requests.
- A signed token can be verified without retrieving a stored copy of that token.
- It can carry claims such as a subject, expiration time, issuer, audience, and scopes.
- Multiple API services can verify tokens independently when they are configured with the appropriate verification key and validation rules.

### Important distinction

JWT is a **token format**, not an authentication protocol by itself. It does not define how a user logs in, how credentials are checked, or how permissions are granted. Those are responsibilities of the surrounding application or an identity/authorization protocol.

---

## 2. Authentication vs. Authorization

These two concepts are related but different.

| Concept | Question | Example |
|---|---|---|
| Authentication | Who are you? | Verify a user's login or access token |
| Authorization | What are you allowed to do? | Check whether the user can delete an employee |

### Authentication

Authentication establishes an identity or verifies a credential.

For a username/password login:

1. The client submits credentials over HTTPS.
2. The server looks up the account.
3. The server verifies the supplied password against the stored password hash.
4. If the credentials are valid, the server may issue an access token.

For later API calls, the server validates the presented access token.

### Authorization

Authorization determines whether an authenticated identity may perform a particular action.

For example:

- A regular member may view their own profile.
- A member may be allowed to update their own profile.
- Only an administrator may delete other users.

Authorization can use role or scope claims from a verified token, database-backed permissions, policy checks, or a combination.

### Can JWT be used for authorization?

**Yes, JWT claims can carry authorization information**, such as roles or scopes. The API can make authorization decisions based on those claims after validating the token.

However, a role inside a token can become stale. For example:

1. A token is issued while a user has the `admin` role.
2. The user's role changes to `member` in the database.
3. The already-issued token still contains `admin`.
4. Until the token expires or is otherwise invalidated, an API relying only on that claim may continue to treat it as an administrator token.

For permissions that must take effect immediately, consult current server-side authorization state or implement a revocation/versioning strategy.

---

## 3. Stateful vs. Stateless Authentication

### 3.1 Stateful (session-based) authentication

In a typical server-side session design:

1. The user logs in.
2. The server creates a session and stores session data in a database or cache.
3. The client receives a session identifier, commonly through a cookie.
4. The client sends that identifier on subsequent requests.
5. The server looks up the session and checks whether it is valid.

```text
Client                  API server                 Session store
  |                         |                            |
  |---- login credentials ->|                            |
  |                         |---- create session ------->|
  |                         |<--- session saved ---------|
  |<--- session cookie -----|                            |
  |                         |                            |
  |---- request + cookie -->|                            |
  |                         |---- lookup session ------->|
  |                         |<--- session data ----------|
  |<--- response -----------|                            |
```

**Advantages**
- Sessions can be revoked centrally.
- The server can update session state immediately.
- The browser can keep the session identifier in a secure, HttpOnly cookie.

**Trade-offs**
- A shared session store or session affinity may be needed when multiple application servers are used.
- Session reads add a dependency on the store.
- The session store must be operated, secured, and scaled.

Horizontal scaling does not make sessions impossible. A shared session store (for example, Redis) is a common solution.

### 3.2 Stateless JWT validation

With a signed JWT, the server can validate the signature and claims without looking up a stored copy of the token.

```text
Client                  API server
  |                         |
  |---- login credentials ->|
  |                         |---- verify credentials
  |                         |---- sign JWT
  |<--- access token -------|
  |                         |
  |---- request + JWT ----->|
  |                         |---- verify signature
  |                         |---- validate claims
  |                         |---- process request
  |<--- response -----------|
```

**Advantages**
- Token signature validation can be performed locally.
- API instances do not need a shared token-session record for ordinary verification.
- Multiple services can validate the token if they trust the issuer and use the correct keys and validation rules.

**Trade-offs**
- A self-contained token is not automatically revocable.
- Claims may become stale before the token expires.
- A stolen bearer token can be replayed while it remains valid.
- Key management and claim validation must be implemented correctly.

### Stateful vs. stateless: comparison

| Aspect | Server-side session | Self-contained signed JWT |
|---|---|---|
| State per login | Stored server-side | Usually encoded in token |
| Validation | Session lookup | Signature and claim checks |
| Immediate revocation | Straightforward with centralized state | Requires extra mechanism or waiting for expiry |
| Horizontal scaling | Shared session store or affinity often needed | Local verification possible across instances |
| Token size | Usually small session ID | Can be larger due to claims and signature |
| Permission freshness | Can be checked against current state | Embedded claims may be stale |
| Main operational concern | Session store and lifecycle | Key management, expiry, revocation |

> **Interview point:** JWT can reduce the need for a per-request session lookup. It does not mean an application will never need a database: it may still load a user, check current permissions, or consult a revocation store.

---

## 4. Structure of a JWT

A common **signed JWT** is a compact JWS with three components:

```text
BASE64URL(HEADER).
BASE64URL(PAYLOAD).
BASE64URL(SIGNATURE)
```

### 4.1 Header

The header contains metadata about the token and its cryptographic operation.

Example:

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- `alg`: signing algorithm, such as `HS256` or `RS256`.
- `typ`: optional media-type hint, commonly `JWT`.

The header is encoded, not encrypted. Do not trust an algorithm merely because a token declares it. The verifier must configure an allowed algorithm independently.

### 4.2 Payload

The payload contains claims: statements about a subject or other token context.

Example:

```json
{
  "sub": "user-123",
  "iss": "https://auth.example.com",
  "aud": "users-api",
  "iat": 1790000000,
  "exp": 1790000900,
  "scope": "users:read users:update"
}
```

The values above are illustrative. The exact claims required depend on the application.

**Do not put secrets in a normal signed JWT payload.** Base64URL encoding is reversible. Anyone who obtains the token can decode its payload.

Avoid putting passwords, password hashes, API keys, payment details, or other sensitive data in it.

### 4.3 Signature

For a signed JWT, the signature protects the encoded header and payload against undetected modification and lets the verifier check that the token was signed by a holder of the relevant key.

For HS256, conceptually:

```text
signing_input = base64url(header) + "." + base64url(payload)

signature = HMAC-SHA256(signing_input, shared_secret)
```

The final token is:

```text
base64url(header).base64url(payload).base64url(signature)
```

The signature is **not encryption**. It does not hide the payload.

### Is every JWT three parts?

No. A typical signed JWT (JWS compact serialization) has three parts. An encrypted JWT (JWE compact serialization) has five parts. Most application examples that say “JWT” refer to a signed, three-part token.

---

## 5. How JWT Signing and Verification Work

### 5.1 Token creation

After successful login, the issuer prepares claims, signs them with a configured key, and returns the token.

For example, an access token may contain:

```json
{
  "sub": "user-123",
  "exp": 1790000900
}
```

The `sub` claim identifies the subject; the `exp` claim limits the token's validity period.

### 5.2 Token verification

When a client sends:

```http
GET /users/profile
Authorization: Bearer <access-token>
```

The API typically:

1. Extracts the bearer token.
2. Parses the token.
3. Verifies its signature using the expected algorithm and key.
4. Validates required claims and policy constraints, such as `exp`, `iss`, and `aud` where applicable.
5. Uses validated identity and authorization information to handle the request.

If signature validation fails, the token must not be trusted. If required claims are missing or invalid, reject it according to the application's policy.

### 5.3 Why does the signature stop payload tampering?

Suppose a token contains:

```json
{
  "sub": "gopal",
  "role": "member"
}
```

An attacker edits the payload to:

```json
{
  "sub": "gopal",
  "role": "admin"
}
```

The attacker can encode the new JSON, but cannot generate a valid signature for the modified content without the appropriate signing key.

The backend recomputes or verifies the signature against the token's header and payload. The changed token will fail verification.

### 5.4 What a valid signature proves—and what it does not

A valid signature indicates that the signed bytes match a signature made using the corresponding signing key, subject to the trust placed in that key.

It does **not** prove:
- that the token has not been stolen;
- that the user is still active;
- that embedded roles are still current;
- that the token is intended for this particular API unless `aud` is checked;
- that the payload is confidential.

Use HTTPS to protect tokens in transit. A signature is not a substitute for TLS.

---

## 6. HS256 vs. RS256

JWT commonly uses either a symmetric or an asymmetric signing algorithm.

### 6.1 HS256 (HMAC using SHA-256)

HS256 uses the same shared secret to sign and verify.

```text
Issuer:
  header + payload + shared secret
              |
              v
          HS256 HMAC
              |
              v
           signature

Verifier:
  token + same shared secret
              |
              v
        verify signature
```

**Key characteristic:** Any service that can verify an HS256 token using the shared secret can also create valid HS256 tokens.

Use a strong, randomly generated secret and protect it as a credential. Do not use a short, guessable password as the signing key.

### 6.2 RS256 (RSA using SHA-256)

RS256 uses an asymmetric key pair:

- Private key signs the token.
- Corresponding public key verifies it.

```text
Issuer:
  header + payload + private key
              |
              v
           RS256
              |
              v
           signature

Verifier:
  token + public key
              |
              v
        verify signature
```

A public key can be distributed to API services without giving them the ability to mint RS256 tokens.

### 6.3 Comparison

| Feature | HS256 | RS256 |
|---|---|---|
| Key type | Shared secret | Private/public key pair |
| Signing key | Secret | Private key |
| Verification key | Same secret | Public key |
| Can a verifier mint tokens? | Yes, if it has the secret | Not with only the public key |
| Key distribution | Secret must be shared with verifiers | Public key can be distributed |
| Common fit | A single trusted service or tightly controlled deployment | Multiple services that should verify but not issue tokens |

Neither algorithm is universally better. Choose based on the architecture and operational requirements. Configure the allowed algorithms explicitly and never select the verification algorithm solely from untrusted token input.

### 6.4 Public key and private key: are they the same?

No. They are different but mathematically related.

- The private key must remain secret and is used to sign.
- The public key can be shared and is used to verify.
- A public key does not provide a practical way to derive the private key.

For RS256, an API service can verify tokens issued by an authentication service without receiving its private key.

---

## 7. JWT Authentication Flow

A simple first-party username/password login flow can look like this:

```text
                 LOGIN
Client ------------------------------> FastAPI
       username + password               |
                                          | Look up user
                                          | Verify password hash
                                          |
                              valid       | invalid
                          +---------------+--------------+
                          |                              |
                          v                              v
                  Create access JWT                Return 401
                          |
                          v
Client <------------- access token
  |
  | Subsequent request:
  | Authorization: Bearer <token>
  v
FastAPI
  |
  | Extract token
  | Verify signature
  | Validate expiry and expected claims
  | Resolve current user / permissions if required
  |
  +---- valid and authorized ----> Protected response
  |
  +---- invalid -----------------> 401 Unauthorized
  |
  +---- authenticated but denied -> 403 Forbidden
```

### Typical HTTP status codes

| Status | Meaning | Typical authentication/authorization example |
|---|---|---|
| `200 OK` | Request succeeded | Authorized request returned data |
| `201 Created` | Resource created | Successful user creation |
| `400 Bad Request` | Invalid request | Malformed application input |
| `401 Unauthorized` | Missing or invalid authentication | Missing, expired, or invalid bearer token |
| `403 Forbidden` | Authenticated but not permitted | Member attempts an admin-only action |
| `404 Not Found` | Resource not found | Requested user does not exist |
| `422 Unprocessable Content` | Request validation failed | FastAPI request validation error |
| `500 Internal Server Error` | Unexpected server failure | Unhandled server-side error |

A `401` response commonly includes:

```http
WWW-Authenticate: Bearer
```

---

## 8. Access Tokens and Refresh Tokens

Access and refresh tokens serve different purposes.

### 8.1 Access token

An access token is presented to a resource server to access protected resources.

Typical characteristics:
- Short-lived.
- Sent with API requests, usually in the `Authorization` header.
- Should carry only the privileges needed for its purpose.
- May be a JWT or an opaque token.

An example access-token response:

```json
{
  "access_token": "<access-token>",
  "token_type": "bearer",
  "expires_in": 900
}
```

`expires_in` is an example of a 15-minute lifetime, not a universal recommendation.

### 8.2 Refresh token

A refresh token is presented to the authorization server/token endpoint to obtain a new access token. It is not normally sent to every resource API.

Typical characteristics:
- Longer-lived than an access token, depending on policy.
- Must be protected carefully because it can be used to obtain new access tokens.
- Often stored as server-side state or represented by an opaque random value.
- Should have a defined rotation, expiration, and revocation policy.

### 8.3 Why use both?

Suppose an access token expires after a short interval. Without a refresh mechanism, the user may have to authenticate again frequently.

A refresh token lets the client request a new access token without asking the user to re-enter the password each time.

```text
Client                 Authorization server         Resource API
  |                              |                         |
  |---- login/authorization ---->|                         |
  |<--- access + refresh --------|                         |
  |                              |                         |
  |---- request with access token ------------------------>|
  |<--- protected response -------------------------------|
  |                              |                         |
  |       access token expires   |                         |
  |                              |                         |
  |---- refresh token ---------->|                         |
  |<--- new access token --------|                         |
  |                              |                         |
  |---- request with new access token -------------------->|
```

When refresh-token rotation is used, the server issues a new refresh token and invalidates the old one. Reuse of an already-invalidated refresh token can indicate replay or theft and should be handled according to the security policy.

### 8.4 JWT refresh token vs. opaque refresh token

| Type | Description |
|---|---|
| JWT refresh token | A structured token whose claims can be cryptographically validated |
| Opaque refresh token | A random, non-self-describing value that the server resolves using stored state |

An opaque refresh token is often convenient because refresh-token rotation, revocation, device/session management, and reuse detection naturally require server-side state. A JWT refresh token is not automatically safer or easier to revoke.

### 8.5 Logout and revocation

Deleting a JWT from the client does not invalidate a copy already stolen by an attacker. A stateless access token will normally remain usable until expiry unless the system adds a revocation or sender-constraining mechanism.

Common choices include:
- Short-lived access tokens.
- Refresh-token revocation.
- Refresh-token rotation and reuse detection.
- A token denylist keyed by `jti` until the token expires.
- A user/token version checked against server-side state.
- Sender-constrained tokens, such as DPoP or mutual TLS, where suitable.

Each revocation or current-state check adds complexity and may introduce a state lookup. Choose based on the security and availability requirements.

---

## 9. JWT vs. OAuth 2.0 vs. OpenID Connect

These terms are often mixed up, but they are not interchangeable.

| Term | What it is | Main purpose |
|---|---|---|
| JWT | Token format | Represents claims in a compact form |
| OAuth 2.0 | Authorization framework | Allows a client to obtain delegated access to protected resources |
| OpenID Connect (OIDC) | Identity layer built on OAuth 2.0 | Adds user authentication and identity claims |

### OAuth 2.0

OAuth 2.0 defines roles and flows for obtaining and using access tokens. It does not require access tokens to be JWTs; tokens may be opaque.

### OpenID Connect

OIDC adds an authentication layer to OAuth 2.0. An ID token is generally a JWT that communicates authentication information to an OIDC client. An ID token is not a substitute for an API access token.

### FastAPI's `OAuth2PasswordBearer`

Example:

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login/"
)
```

- `OAuth2PasswordBearer` is a FastAPI security helper/class.
- `oauth2_scheme` is simply a variable name holding an instance of that class.
- It extracts the bearer token from the `Authorization` header and integrates the security scheme with OpenAPI docs.
- It does **not**, by itself, verify a JWT signature, check a user in the database, or implement a complete authorization server.

The `tokenUrl` describes the token endpoint for OpenAPI; it does not make FastAPI create that endpoint automatically.

### Important note about the password grant

FastAPI examples demonstrate the OAuth2 password flow for teaching purposes. Current OAuth 2.0 security best practice says the Resource Owner Password Credentials grant must not be used for new OAuth deployments. For user-facing applications, use a suitable Authorization Code flow with PKCE through an identity provider. For service-to-service clients, use an appropriate machine-to-machine flow, such as Client Credentials, when applicable.

A custom endpoint that accepts a username and password and issues a JWT can be useful for learning, but it should not automatically be described as a complete, standards-compliant OAuth authorization server.

---

## 10. JWT in FastAPI

This section demonstrates the core mechanics using **PyJWT**. It is an educational example; production applications should also account for password policy, rate limiting, secret management, HTTPS, logging hygiene, key rotation, account status, and the application's authorization rules.

### 10.1 Install dependencies

```bash
pip install fastapi uvicorn pyjwt pwdlib[argon2]
```

`pwdlib` with Argon2 is used here for password hashing. Existing projects may use another well-configured password-hashing library.

### 10.2 Configure token creation and verification

For a single-service example using HS256:

```python
import os
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
ISSUER = "https://auth.example.com"
AUDIENCE = "users-api"
ACCESS_TOKEN_EXPIRE_MINUTES = 15


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        audience=AUDIENCE,
        options={
            "require": ["sub", "iat", "exp"],
        },
    )
```

**Notes:**
- `SECRET_KEY` must be a strong random secret supplied through a secure configuration mechanism, not committed to source control.
- For HS256, use at least 256 bits of random key material.
- The algorithm is configured by the application and explicitly allowlisted during decoding.
- `exp` defines when the token expires.
- `iss` identifies the issuer.
- `aud` identifies the intended recipient/API.
- `sub` identifies the subject.
- `iat` records when the token was issued.
- `require` makes selected claims mandatory; a claim being present does not by itself mean every possible claim has been validated for your use case.

A simple secret can be generated once using a cryptographically secure random generator, for example:

```python
import secrets

print(secrets.token_urlsafe(32))
```

Generate the value securely and store it in a secret manager or protected environment configuration. Do not generate a new signing key at each application startup, or previously issued tokens will become unverifiable after a restart.

### 10.3 Extract and validate a token in FastAPI

```python
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/login/"
)


def get_current_subject(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject:
            raise credentials_exception

        return subject

    except InvalidTokenError:
        raise credentials_exception


@app.get("/profile")
def read_profile(
    subject: Annotated[str, Depends(get_current_subject)],
):
    return {"subject": subject}
```

When a request reaches `/profile`:
1. `OAuth2PasswordBearer` extracts the bearer token.
2. `get_current_subject()` calls `decode_access_token()`.
3. PyJWT verifies the signature and the configured claims.
4. The endpoint receives the validated subject.

This example returns the subject from the token. An application that needs current account state can load the user from the database and check whether the account is active.

### 10.4 Add authorization checks

Authentication alone does not mean the user can perform every operation.

For example, a project could use a dependency to require an administrator:

```python
from fastapi import Depends, HTTPException, status


def require_admin(
    current_user=Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin=Depends(require_admin),
):
    # Perform the deletion here.
    return {"deleted_user_id": user_id}
```

`get_current_user` is an application-specific function that should validate the token and resolve the corresponding user. The sample assumes the user model has an `is_admin` field.

For a self-service update route, also verify that the authenticated user is allowed to update the requested resource. Never trust a user ID supplied in the URL as proof of identity.

### 10.5 Where does `OAuth2PasswordRequestForm` fit?

A login endpoint may use:

```python
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm

@app.post("/users/login/")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    # Look up form_data.username.
    # Verify form_data.password against the stored password hash.
    # Issue and return an access token after successful verification.
    ...
```

`OAuth2PasswordRequestForm` parses form fields such as `username` and `password`. It does not hash passwords, verify credentials, create JWTs, or validate bearer tokens on protected endpoints. Those are separate responsibilities.

For new OAuth-based systems, prefer the currently recommended OAuth flow rather than adopting the password grant simply because it appears in a framework tutorial.

### 10.6 How your CRUD endpoints should handle authentication

For a typical user API:

| Endpoint | Usually public? | Typical protection |
|---|---:|---|
| `POST /users/create/` | Depends on product policy | Public registration may be allowed; otherwise require authorization |
| `POST /users/login/` | Yes | Verify credentials and issue tokens |
| `GET /users/me` | No | Valid access token |
| `PUT /users/{id}` | No | Valid token plus ownership or admin check |
| `DELETE /users/{id}` | Usually no | Valid token plus explicit permission, often admin-only |

Do not confuse adding `Depends(get_current_user)` with completing authorization. A user who is authenticated may still be forbidden from deleting another user's account.

---

## 11. JWT Security Best Practices

### 11.1 Always use HTTPS

Bearer tokens are usable by whoever possesses them. HTTPS helps protect them from being read or modified in transit.

Avoid sending tokens in URL query parameters because URLs can be logged, copied, cached, or exposed in browser history and referrer data.

### 11.2 Keep access tokens short-lived

A short lifetime limits the time window in which a stolen access token may be used. Choose a lifetime that balances security, user experience, refresh behavior, and application risk.

Short expiry is not a complete revocation strategy.

### 11.3 Validate the signature and claims

At minimum, define and enforce the expected:
- signing algorithm;
- verification key;
- expiration policy;
- issuer (`iss`), where used;
- audience (`aud`), where used;
- subject (`sub`) format and meaning.

For tokens with `nbf`, validate that the token is not being used before its valid-from time. Use a small clock-skew allowance only when justified.

Do not merely decode the payload and trust its fields.

### 11.4 Pin allowed algorithms

Do not choose the algorithm from untrusted token input. Configure the expected algorithm(s) and compatible keys in trusted application configuration.

Do not mix symmetric and asymmetric algorithm families in a way that lets attacker-controlled token headers affect how a key is interpreted.

### 11.5 Protect signing keys

- Keep secrets out of source control.
- Use environment configuration or a secrets manager.
- Limit access to the signing key.
- Have a key-rotation plan.
- Avoid logging keys or full tokens.
- For asymmetric signing, keep private keys only where signing is required.

If a signing key is compromised, an attacker may be able to mint tokens that pass verification until the key is distrusted or rotated out.

### 11.6 Store tokens carefully on the client

**Browser applications**
- `HttpOnly` cookies prevent JavaScript from reading the cookie, reducing token theft through some XSS scenarios.
- `Secure` cookies are sent only over HTTPS.
- Choose an appropriate `SameSite` policy.
- Cookie-based authentication needs a CSRF strategy appropriate to the application's request patterns.
- Keeping short-lived access tokens in memory and refresh tokens in a secure HttpOnly cookie is one possible architecture, not a universal rule.

**Native mobile applications**
- Use platform-provided secure storage such as the iOS Keychain or Android Keystore-backed storage, according to the platform's capabilities.

Avoid treating local storage as automatically secure against XSS.

### 11.7 Use least privilege

Give tokens only the minimum scope or privileges required. Restrict tokens to the intended API using `aud` where appropriate.

For example, a read-only token should not also grant user deletion.

### 11.8 Plan for revocation and account changes

Decide how the system handles:
- logout;
- password changes;
- disabled or deleted accounts;
- changed roles;
- refresh-token theft;
- compromised devices.

Possible approaches include short access-token lifetimes, server-side token/session records, token versioning, denylisting, and refresh-token rotation. Every approach has operational trade-offs.

### 11.9 Do not put sensitive data in a signed payload

A signed JWT is generally readable by the token holder. Signing provides integrity/authenticity, not confidentiality. If confidentiality is genuinely required, use an appropriate encryption design (JWE where suitable) or avoid putting that data in the token.

### 11.10 Be careful with logging

Do not write bearer tokens, refresh tokens, passwords, or signing secrets to application logs. Log safe metadata such as request IDs, subject identifiers where policy permits, and failure categories.

---

## 12. Limitations and Trade-offs

### 12.1 Revocation is not automatic

A signature check proves that the token is validly signed; it does not tell the server whether the user logged out moments ago. Stateless access tokens are usually valid until expiry unless additional checks are implemented.

### 12.2 Stale claims

A token can preserve an old role, scope, or account status. Keep lifetimes appropriate and perform current-state checks for sensitive actions.

### 12.3 Token theft and replay

A bearer token can be replayed by someone who steals it. Protect it in transit and at rest, use short lifetimes, and consider sender-constrained tokens for higher-risk systems.

### 12.4 Token size

JWTs carry claims and a signature. Larger payloads increase request size and may be repeated on every API call. Keep tokens compact.

### 12.5 Operational complexity

JWT shifts some work from a session store to cryptographic key management, claim validation, expiry policy, and revocation design. It is not automatically simpler or more scalable for every application.

---

## 13. Common Misconceptions

| Misconception | Correction |
|---|---|
| JWT is encrypted by default. | A typical signed JWT is encoded and signed, not encrypted. |
| JWT is an authentication protocol. | JWT is a token format. Login and authorization are defined by the surrounding system or protocol. |
| JWT means no database is ever needed. | Signature validation can be stateless, but user lookup, permissions, revocation, and audit needs may require state. |
| A valid signature means the user is authorized for everything. | Signature verification authenticates the token; authorization still needs policy checks. |
| JWT cannot be used for authorization. | Verified claims can inform authorization, but stale permissions and revocation need consideration. |
| `OAuth2PasswordBearer` verifies the JWT. | It extracts a bearer token and describes a security scheme; application code or another component must validate the token. |
| Logging out deletes a JWT on the server. | In a stateless design, deleting it on the client does not invalidate stolen copies. |
| Public keys and private keys are the same. | They are distinct and mathematically related. In RS256, private signs and public verifies. |
| Every JWT has three parts. | Signed compact JWS JWTs commonly have three; compact JWE has five. |
| JWT is always better than sessions. | The right choice depends on revocation, architecture, client type, security, and operational needs. |

---

## 14. Interview Questions and Answers

### Q1. What is JWT?

JWT is a compact, URL-safe format for carrying claims between parties. A signed JWT allows a verifier to check the integrity of the token and that it was signed by a trusted key.

### Q2. What are the three parts of a typical signed JWT?

Header, payload, and signature, separated by dots. The header and payload are Base64URL-encoded; the signature is generated over the signing input.

### Q3. Is JWT encrypted?

Not by default. A common signed JWT is readable by anyone who has it. Its signature protects integrity and authenticity, not confidentiality.

### Q4. Why is a JWT signature important?

It lets the server detect changes to the signed content and verify that it matches a signature generated using the expected signing key.

### Q5. How can the backend validate a JWT if it does not store it?

The backend verifies the token's signature using a configured key and validates the necessary claims. It does not need a stored token copy for ordinary cryptographic verification.

### Q6. Does JWT eliminate database calls?

No. JWT may eliminate the need for a session lookup solely to validate the token. The application may still query the database for the user, account status, current roles, resource ownership, or revocation state.

### Q7. What is the difference between HS256 and RS256?

HS256 uses a shared secret for signing and verification. RS256 uses a private key for signing and a corresponding public key for verification.

### Q8. Why is RS256 useful in a microservices architecture?

It allows services to verify tokens using a public key without sharing the private signing key. Only trusted signers need access to the private key.

### Q9. What is the difference between authentication and authorization?

Authentication establishes or verifies identity. Authorization checks what that identity is permitted to do.

### Q10. Can JWT be used for authorization?

Yes. A verified JWT can carry roles or scopes used in authorization decisions. However, embedded claims may become stale, so sensitive permission checks may need current server-side state.

### Q11. What is the difference between an access token and a refresh token?

An access token is presented to a resource API to access protected resources. A refresh token is presented to an authorization server to obtain a new access token. Refresh tokens require especially careful storage, rotation, and revocation.

### Q12. What happens when a JWT expires?

A correctly configured verifier rejects it. The client may obtain a new access token through a valid refresh mechanism or require the user to authenticate again.

### Q13. What is the `sub` claim?

`sub` is the subject claim, identifying the principal the token is about. Applications commonly use it for a stable user or service identifier.

### Q14. What are `exp`, `iat`, `iss`, and `aud`?

- `exp`: expiration time.
- `iat`: issued-at time.
- `iss`: issuer.
- `aud`: intended audience or recipient.

They are registered JWT claim names. A verifier should validate the claims relevant to its token contract.

### Q15. What is a bearer token?

A bearer token is a credential that can be used by whoever possesses it. It is commonly sent in the HTTP `Authorization` header as `Bearer <token>`.

### Q16. What does `OAuth2PasswordBearer` do in FastAPI?

It extracts the bearer token from the `Authorization` header and declares an OAuth2 bearer security scheme for OpenAPI. It does not, by itself, validate JWT signatures or load users.

### Q17. Why do we use `Depends(get_current_user)`?

It lets FastAPI resolve a shared authentication dependency before an endpoint runs. The dependency can extract and validate a token and return the current user. Authorization checks may still be needed.

### Q18. What is the difference between 401 and 403?

`401 Unauthorized` means the request lacks acceptable authentication credentials. `403 Forbidden` means the server understood the request but refuses to authorize it. In API practice, an authenticated user lacking permission commonly receives 403.

### Q19. Can a JWT be revoked before it expires?

Not automatically in a purely stateless design. Early revocation requires an additional mechanism, such as a denylist, token version, server-side session/grant state, or a short-lived access-token strategy paired with revocable refresh tokens.

### Q20. What happens if an attacker changes the role in a JWT payload?

The modified payload no longer matches the original signature. Without the appropriate signing key, the attacker cannot produce a valid replacement signature, so a correctly verifying API rejects the modified token.

### Q21. Does JWT protect against man-in-the-middle attacks?

The signature protects the signed content from undetected modification, but it does not provide transport confidentiality or prevent token theft. HTTPS/TLS is needed to protect tokens in transit.

### Q22. Why should access tokens be short-lived?

A short lifetime limits the period during which a stolen token can be used. It does not eliminate the need to protect tokens or plan for revocation.

### Q23. Should passwords be stored in a JWT?

No. Passwords and other secrets should not be placed in the payload. The payload is generally readable by whoever possesses the token.

### Q24. Is OAuth the same as JWT?

No. OAuth 2.0 is an authorization framework; JWT is a token format. OAuth access tokens may be JWTs or opaque tokens.

### Q25. What is the difference between JWT and OpenID Connect?

JWT is a token format. OpenID Connect is an identity layer on top of OAuth 2.0. OIDC commonly uses a JWT as an ID token to convey authentication information to a client.

---

## 15. Quick Revision Cheat Sheet

### Core concepts

- **JWT:** Compact representation of claims.
- **Header:** Token metadata, including algorithm.
- **Payload:** Claims such as subject, issuer, audience, and expiry.
- **Signature:** Integrity and authenticity check for signed content.
- **Bearer:** Whoever possesses the token can present it as a credential.
- **Authentication:** Who are you?
- **Authorization:** What can you do?
- **Access token:** Used to access protected resources.
- **Refresh token:** Used to obtain new access tokens.
- **OAuth 2.0:** Authorization framework.
- **OIDC:** Authentication/identity layer built on OAuth 2.0.

### Critical distinctions

```text
JWT != OAuth
JWT != encryption
Signature != authorization
Stateless validation != no database
Deleting token on client != server-side revocation
OAuth2PasswordBearer != JWT signature verification
```

### RS256 vs. HS256 in one line

```text
HS256: shared secret signs and verifies.
RS256: private key signs; public key verifies.
```

### Typical protected API flow

```text
Request
  -> Extract Bearer token
  -> Verify signature with an allowlisted algorithm
  -> Validate required claims (e.g. exp, iss, aud)
  -> Resolve identity if required
  -> Apply authorization policy
  -> Execute endpoint
```

### Interview summary

> JWT is a compact token format commonly used for stateless access-token validation. The backend verifies a signed token with a configured key and checks its relevant claims. JWT can carry authorization claims, but authorization remains a separate policy decision. JWT reduces the need for a per-request session lookup, while revocation, stale claims, token theft, and key management remain important design considerations.

---

## 16. References

These primary references are useful for deeper study:

1. **RFC 7519 — JSON Web Token**  
   https://www.rfc-editor.org/rfc/rfc7519

2. **RFC 8725 — JSON Web Token Best Current Practices**  
   https://www.rfc-editor.org/rfc/rfc8725

3. **RFC 9700 — Best Current Practice for OAuth 2.0 Security**  
   https://www.rfc-editor.org/rfc/rfc9700

4. **FastAPI — Security: First Steps**  
   https://fastapi.tiangolo.com/tutorial/security/first-steps/

5. **FastAPI — Simple OAuth2 with Password and Bearer**  
   https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/

6. **PyJWT — Usage Examples**  
   https://pyjwt.readthedocs.io/en/stable/usage.html

7. **PyJWT — API Reference**  
   https://pyjwt.readthedocs.io/en/latest/api.html

---

**End of notes**
