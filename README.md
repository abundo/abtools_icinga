# abtools_icinga

# Installation

todo

# Scripts

## sync_elements_to_icinga.py

Fetches the list of elements from Element API, and writes icinga2 configuration files
If configuration has changed, asks icinga2 to reload the changes


## mail_notification.py

Called when icinga wants to notify/send email.

In addition to the current issue (host/service up/down), the script alsow fetches all 
unacknowledged hosts and services, and adds them to the end of the email. It makes
it much easier to see current status. If multiple emails are sent, delete all except the
last one - there you have current status.
