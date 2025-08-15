# Security

This document outlines common risks and possible best practices for the HTTP request Lego provider charm. It focuses on configurations and protections available through the charm itself.

## Risks

The following items include descriptions of the risks, their corresponding best practices for mitigation, as well as links to related documentation and configuration guidelines.

### Loss of data

- The PostgreSQL database might become destroyed, corrupted, or may be destroyed.
- The Git repository might become destroyed, corrupted, or may be destroyed.

#### Best practices
  
- Configure repository backups:

  Back up the Git repository with the appropriate strategy depending on your server.

### Security vulnerabilities

Running HTTP request Lego provider with one or more weaknesses that can be exploited by attackers.

#### Best practices

- Keep the Juju and the charm updated. See more about Juju updates in the [documentation](https://documentation.ubuntu.com/juju/latest/explanation/juju-security/index.html#regular-updates-and-patches).
