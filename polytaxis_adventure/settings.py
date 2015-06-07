import json
import os
import pkg_resources

import appdirs

def res(path):
    return pkg_resources.resource_string('polytaxis_adventure', path)

with open(res('style.json'), 'r') as style_file:
    style_settings = json.load(style_file)

style_settings = {
    frozenset(key.split(' ')): value
    for key, value in style_settings.items()
}
