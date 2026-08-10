---
name: "smart-email-self-login"
description: "Email assistant skill with self-login capability - clients can securely login to their email themselves without sharing credentials with the agent"
---

# Smart Email - Self Login Feature

## Overview

This enhancement adds self-login functionality to the Smart Email skill, allowing clients to authenticate with their email providers directly without sharing credentials with the agent.

## Problem

The current Smart Email skill requires users to provide email passwords to the agent, which creates security concerns. Users want to authenticate themselves first and then grant the agent access.

## Solution

### 1. Self-Login Web Interface

Create a secure web interface where users can:

- Enter their email address
- Choose authentication method (OAuth2 for supported providers, App Password for others)
- Complete the login process securely
- Receive a unique access token

### 2. OAuth2 Self-Login Flow

For email providers that support OAuth2:

1. User enters email and clicks "Login with OAuth2"
2. System redirects to provider's OAuth consent screen
3. User authorizes the application
4. System receives authorization code
5. System exchanges code for access token
6. Token stored locally, user gets access token

### 3. App Password Self-Login Flow

For providers requiring app passwords (like Gmail):

1. User gets guided instructions to create an app password
2. User enters the app password in a secure interface
3. Password used only locally (never stored in agent memory)
4. User receives session-specific access token

### 4. Integration Process

Once authenticated, the agent can:

- Use the provided access token to access emails
- Process and summarize emails
- Generate reports
- Forward specific emails based on user instructions
- All actions are performed within the authenticated session

## Technical Implementation

### Authentication Methods

1. **OAuth2 (Primary)**: Works with:
   - Google Workspace/G Suite
   - Microsoft 365/Outlook
   - Other OAuth2-compliant providers

2. **App Password**: For legacy systems or providers without OAuth2 support

### Security Features

- No credentials stored in agent memory
- Tokens are temporary and time-limited
- Secure web interface with HTTPS support
- Token validation before any email access
- Automatic token refresh when needed

### User Experience

1. Simple, guided setup interface
2. Clear instructions for each authentication method
3. Progress indicators during the login process
4. Success confirmation with next steps
5. Ability to logout and re-authenticate easily

## Usage Examples

### Self-Login via Web Interface

```bash
# Start web interface for self-login
node smart-email/server.js --port 3900

# Open the URL shown in terminal
# User enters email and chooses authentication method
# Complete login process securely
# Copy the generated access token
```

### Integration with Agent

```bash
# Use the access token for authenticated operations
node smart-email/cli.js check --token <ACCESS_TOKEN>
node smart-email/cli.js digest --token <ACCESS_TOKEN> --since 1440
```

## Benefits

- **Security**: No credential sharing
- **Convenience**: Self-service authentication
- **Flexibility**: Multiple authentication methods
- **Transparency**: Clear authentication flow
- **Control**: Users control their own authentication

## Files Modified

1. **server.js**: Enhanced web interface with self-login capabilities
2. **oauth.js**: Extended OAuth2 support for additional providers
3. **store.js**: Added session-based token management
4. **cli.js**: Added token-based authentication for CLI commands
5. **SKILL.md**: Updated documentation with self-login instructions

## Configuration

### Required Setup

1. Install dependencies: `npm install`
2. Start web interface: `node server.js`
3. Access web interface via provided URL
4. Follow self-login instructions

### Token Management

Tokens are stored locally with automatic expiration and refresh. Tokens are validated before any email operations.

## Security Considerations

- Tokens are temporary (typically 1 hour)
- Automatic token refresh implemented
- No persistent credential storage
- Secure web interface with proper validation
- Rate limiting on authentication attempts

## Testing

Test the self-login feature:

1. Start web interface
2. Test with different email providers
3. Verify token-based operations
4. Test token expiration and refresh
5. Check security features

## Future Enhancements

- Support for additional OAuth2 providers
- Multi-factor authentication support
- Enhanced security monitoring
- Integration with external authentication services
- Mobile-friendly interface
