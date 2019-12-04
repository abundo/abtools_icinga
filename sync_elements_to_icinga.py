#!/usr/bin/env python3
111
"""
Get list of elements from 'element API'

Write configuration file for icinga2

Dependency:
    pip3 install orderedattrdict
"""

import os
import sys
import requests
import yaml
from orderedattrdict import AttrDict

sys.path.insert(0,"/opt")
import ablib.utils as utils
from ablib.email1 import Email
from ablib.icinga import Icinga


# ----- Start of configuration items -----

CONFIG_FILE="/etc/abtools/abtools_icinga.yaml"

# ----- End of configuration items -----

users = {}   # Key is email address


# Load configuration file
config = utils.load_config(CONFIG_FILE)

icinga = Icinga(config=config.icinga)


def create_conf_file(filename, message=""):
    """
    Create a new configuration file, with header
    """
    f = open(filename, "w")
    f.write("//\n")
    f.write("// Auto-generated. Note: do not edit this file, your changes will be overwritten/lost\n")
    if message:
        f.write("// %s\n" % message)
    f.write("//\n")
    f.write("\n")
    return f


def write_elements(api_elements, changed=False):
    """
    """
    print("Writing config:", config.icinga_sync.hosts_file.tmp)
    f = create_conf_file(config.icinga_sync.hosts_file.tmp, "%s hosts" % len(api_elements))

    for element in api_elements.values():
        if element["active"]:
            _options = []

            if "parents" in element and element["parents"]:
                _options.append("  vars.pe_parents = [")
                for parent in element["parents"]:
                    _options.append('    %s,' % icinga.quote(parent))
                _options.append("  ]")

            if "alarm_destination" in element and element["alarm_destination"]:
                _options.append("  vars.pe_alarm_destination = [")
                for destination in element["alarm_destination"]:
                    _options.append('    %s,' % icinga.quote(destination))
                    if destination not in users:
                        users[destination] = 1
                _options.append("  ]")
            else:
                _options.append(config.icinga_sync.default_notification)

            if "alarm_timeperiod" in element and element["alarm_timeperiod"]:
                _options.append('  vars.pe_alarm_timeperiod = %s' % icinga.quote(element["alarm_timeperiod"]))

            element["_options"] = "\n".join(_options)
            element["comments"] = icinga.quote(element["comments"])
            f.write(config.icinga_sync.host_template.format_map(element))
        else:
            print("Ignoring %s, element is not active" % element["hostname"])

    # Write dependencies
    f.write("// %s\}\n" % ("*"*76))
    for hostname, element in api_elements.items():
        if element["active"]:
            if "parents" in element and element["parents"]:
                parents = element.get("parents", None)
                if parents:
                    for parent in parents:
                        if parent in api_elements:
                            if api_elements[parent]["active"]:
                                depname = "host-%s_host-%s" % (parent, hostname)
                                f.write(
"""
object Dependency "%s" {
    parent_host_name = "%s"
    child_host_name = "%s"
    ignore_soft_states = false
}
""" % (depname, parent, hostname))
                            else:
                                print("Error: Unknown parent %s on hostname %s" % (parent, hostname))

    f.write("\n")
    f.close()

    t = config.icinga_sync.hosts_file
    changed = utils.install_conf_file(src=t.tmp, 
                                      dst=t.dst, 
                                      changed=changed)
    return changed


def write_users(changed=False):
    """
    Write all email destinations, as users
    """
    print("Writing config:", config.icinga_sync.users_file.tmp)
    f = create_conf_file(config.icinga_sync.users_file.tmp)
    for destination in users:
        d = AttrDict()
        d.username = destination
        d.displayname = destination
        d.email = destination
        f.write(config.icinga_sync.user_template.format_map(d))

    f.close()

    t = config.icinga_sync.users_file
    changed = utils.install_conf_file(src=t.tmp,
                                      dst=t.dst, 
                                      changed=changed)
    return changed


def main():
    print("-" * 79)
    print("Get list of elements from 'elements API'")
    print("   ", config.elements.api.url)
    r = requests.get(config.elements.api.url)
    tmp_api_elements = r.json()
    # print("tmp_api_elements", tmp_api_elements)
    # sys.exit(1)

    print("-" * 79)
    print("Checking elements to monitor")
    api_elements = {}  # Key is hostname
    for hostname, element in tmp_api_elements.items():
        if "monitor_icinga" in element and element["monitor_icinga"] == False:
            print("  Ignoring '%s', 'monitor_icinga' is False" % hostname)
            continue
        api_elements[hostname] = element

    utils.write_etc_hosts_file(api_elements)


    changed = False   # Default, no changes => no reload
    changed = write_elements(api_elements, changed=changed)
    changed = write_users(changed=changed)
    
    if changed:
        print("Reloading icinga, with new configuration")
        icinga.reload()
    else:
        print("No change in icinga configuration")

if __name__ == "__main__":
    try:
        main()
    except:
        # Error in script, send traceback to developer
        utils.send_traceback()
