# Shared module ownership on Frappe v15

AV Tools owns AuthOTP, Feedback, AI Integration and Trade In. CSF TZ must not
register these module names or re-import their standard DocType definitions.

## Fresh sites

Update both apps to the matching version-15-hotfix changes. Make av_tools
available on the bench before installing csf_tz; csf_tz declares it as a required
app. Select av_tools before csf_tz when creating a site in Pilot.

## Existing sites

Back up the site first. If av_tools is not installed, get and install it before
migrating the updated csf_tz. Run a normal site migration after updating both
apps. The migration changes module ownership and re-homes an old OTP Register
whose module is CSF TZ to AuthOTP. It does not delete DocTypes, tables, OTP
records, encrypted secrets or settings.

The AV Tools install hook temporarily removes only approved Module Def rows
so Frappe can register them under av_tools. It refuses collisions owned by
another app, and leaves transaction control to Frappe's installer.

Old csf_tz.authotp registration and validation API paths remain available as
whitelisted wrappers around av_tools. Only AV Tools registers the OTP Customer
and Sales Invoice client scripts and Sales Invoice submission hook.

Removing exported JSON files retires duplicate schema sources; it is not a
request to uninstall csf_tz or delete database records. Other generic DocTypes
and reports shared by these apps are outside this module-registration fix.

## Verify after migration

In the site console, check the app_name of the four Module Def records: each
must be av_tools. Check OTP Register.module is AuthOTP. Compare the number of
OTP Register records before and after migration, and verify an existing OTP
registration and Sales Invoice validation. For fresh sites, confirm that both
apps are installed and creation completes without DuplicateEntryError.
