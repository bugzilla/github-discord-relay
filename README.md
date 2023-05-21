# GitHub Discord Relay

This is an app that can be set as a target for outgoing GitHub webhooks, and can in turn relay those webhook requests to a Discord incoming webhook.

GitHub can already send directly to Discord, but the problem lies when you set up an organization-wide webhook on Discord, and have dozens or more repositories, and want to specify a specific list of repos to include or ignore. Because GitHub itself doesn't have that capability yet. (See [this feature request for GitHub](https://github.com/orgs/community/discussions/36180))

So this is basically a dumb relay, except that it can filter the repositories.

## Installation

This app is designed to run under mod_wsgi on Apache HTTPd, and requires Python 3.8 or newer.

This app has python dependencies, and requires a virtualenv to be set up for it.

* `cd` into the directory containing the app
* `virtualenv venv`
* `pip install -r requirements.txt`

Note that the version of python installed in the virtualenv needs to match the one that mod_wsgi was compiled for.

Place the following in the VirtualHost block for the VirtualHost that will host your app:

``` httpconf
    SetEnv gh2discord_config /path/to/gh2discord_config.json
    WSGIDaemonProcess gh2discord python-home=/path/to/github-discord-relay/venv
    WSGIScriptAlias /github /path/to/github-discord-relay/app.wsgi process-group=gh2discord application-group=%{GLOBAL}
    <Directory /path/to/github-discord-relay>
        Order allow,deny
        Allow from all
    </Directory>
```

You can put the config file wherever you want, as long as you update the SetEnv line above to match where you put it.

The WSGIScriptAlias line above points the /github path after the domain to point at the app. If it's the only thing you have on the domain, you can just leave it as / . Or change it to whatever path you want.

## Config file format

Example config:
``` json
{
  "webhooks": {
    "{webhook id}": {
      "destination_webhook": "https://discord.com/api/webhooks/{random webhook code}/github",
      "include_repositories": [
        "user/repo_name1",
        "user/repo_name2"
      ],
      "exclude_repositories": [
        "user/repo_name3",
        "user/repo_name4"
      ]
    }
  }
}
```

`webhook_id` should be a UUID or similar. It's basically pretty arbitrary. Whatever you use for this would be placed after the url to your app deployment. For example, if your WSGIScriptAlias points at `/webhooks` then your webhook URL that you put in the config on GitHub for thr webhook will be: `https:/my.server.tld/webhooks/{webhook_id}`

`destination_webhook` needs to be the full URL assigned to the webhook by Discord when you set it up in the Discord config, followed by `/github`.

`include_repositories` and `exclude_repositories` are mutually exclusive. You should only use one or the other. If you do provide both for some reason, then `exclude_repositories` will be ignored. Both are a simple list of repositories. Since you can theoretically point more than one organization at the same webhook ID, you need to include the username in front of the repo name.

