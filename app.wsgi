#! env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import os
import json
import requests

def error_log(environ, theError):
    print(theError, file=environ['wsgi.errors'])

def error500_response(environ, start_response, logerror, publicerror):
    status = '500 Internal Server Error'
    output = '<html><head><title>Internal Server Error</title></head>'
    output += '<h1>Internal Server Error</h1>'
    output += "<p>%s</p>" % publicerror
    output = bytes(output, encoding='utf-8')
    response_headers = [('Content-type', 'text/html, charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    error_log(environ, logerror)
    start_response(status, response_headers)
    return [output]

def error401_response(environ, start_response, logerror, publicerror):
    status = '401 Unauthorized'
    output = '<html><head><title>Unauthorized</title></head>'
    output += '<h1>Unauthorized</h1>'
    output += "<p>%s</p>" % publicerror
    output = bytes(output, encoding='utf-8')
    response_headers = [('Content-type', 'text/html, charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    error_log(environ, logerror)
    start_response(status, response_headers)
    return [output]

def error400_response(environ, start_response, logerror, publicerror):
    status = '400 Bad Request'
    output = '<html><head><title>Bad Request</title></head>'
    output += '<h1>Bad Request</h1>'
    output += "<p>%s</p>" % publicerror
    output = bytes(output, encoding='utf-8')
    response_headers = [('Content-type', 'text/html, charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    error_log(environ, logerror)
    start_response(status, response_headers)
    return [output]

def forward_request(environ, start_response, config, webhook_id, body):
    response = requests.post(
            url=config["webhooks"][webhook_id]["destination_webhook"],
            headers={'Content-Type': 'application/json',
                     'User-Agent': environ['HTTP_USER_AGENT'],
                     'Content-Length': environ['CONTENT_LENGTH'],
                     'Accept': environ['HTTP_ACCEPT'],
                     'X-Github-Delivery': environ['HTTP_X_GITHUB_DELIVERY'],
                     'X-Github-Event': environ['HTTP_X_GITHUB_EVENT'],
                     'X-Github-Hook-Id': environ['HTTP_X_GITHUB_HOOK_ID'],
                     'X-Github-Hook-Installation-Target-Id': environ['HTTP_X_GITHUB_HOOK_INSTALLATION_TARGET_ID'],
                     'X-Github-Hook-Installation-Target-Type': environ['HTTP_X_GITHUB_HOOK_INSTALLATION_TARGET_TYPE'],
                     'Connection': 'close'},
            data=body)
    status = "%s %s" % (response.status_code, response.reason)
    start_response(status, list(response.headers.items()))
    return [response.content]

def ignore_request(environ, start_response):
    start_response("204 No Content", [])
    return [""]

def application(environ, start_response):
    if 'gh2discord_config' not in environ:
        return error500_response(environ, start_response,
                "gh2discord_config not specified in Environment.",
                'Configuration error. See error log for details.')

    configfile = environ['gh2discord_config']
    config = {}
    if os.path.isfile(configfile) and os.access(configfile, os.R_OK):
        with open(configfile, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError(msg, doc, pos):
                return error500_response(environ, start_response,
                    "config failed to load: %s" % msg,
                    "Configuration error. See error log for details.")
    else:
        return error500_response(environ, start_response,
                "Configuration file '%s' not found or not readable." % configfile,
                "Configuration error. See error log for details.")

    if "webhooks" not in config:
        return error500_response(environ, start_response,
                "'webhooks' dict is missing from config file.",
                "Configuration error. See error log for details.")

    # PATH_INFO will start with a leading / so drop the first char
    webhook_id = environ["PATH_INFO"][1:]
    if webhook_id not in config["webhooks"]:
        return error401_response(environ, start_response,
                "Invalid webhook: %s" % webhook_id,
                "The webhook you specified does not exist.")

    input = environ['wsgi.input']
    body = input.read(int(environ.get('CONTENT_LENGTH', '0')))
    ghdata = {}
    try:
        ghdata = json.loads(body)
    except json.JSONDecodeError(msg, doc, pos):
        return error400_response(environ, start_response,
                "Payload data is not valid JSON",
                "Payload data is not valid JSON")

    if "repository" not in ghdata:
        # there's no repository to filter, so just forward it
        return forward_request(environ, start_response, config, webhook_id, body)

    repository = ghdata["repository"]["full_name"]
    if "include_repositories" in config["webhooks"][webhook_id]:
        if repository in config["webhooks"][webhook_id]["include_repositories"]:
            return forward_request(environ, start_response, config, webhook_id, body)
        else:
            return ignore_request(environ, start_response)
    if "exclude_repositories" in config["webhooks"][webhook_id]:
        if repository in config["webhooks"][webhook_id]["exclude_repositories"]:
            return ignore_request(environ, start_response)
        else:
            return forward_request(environ, start_response, config, webhook_id, body)
