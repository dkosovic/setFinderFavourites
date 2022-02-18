# Example usage:
# NOTE: Please mind the trailing slashes at the end of the path names!!!
# Supports multiple files per attribute (pass them after a space - see `--add` example below:
# Examples:
# Adding:   `python setFavorites.py --add file:///Users/your_username/your/path/ file:///Users/your_username/your/another_path/`
# Removing: `python setFavorites.py --remove file:///Users/your_username/your/path/`

#!/usr/bin/python

import os
import getpass
import subprocess
import uuid
import logging
import sys
import re
import argparse

import Foundation

favorites_path = "/Users/{user}/Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.FavoriteItems.sfl2"

# Args parser:
parser = argparse.ArgumentParser()
parser.add_argument(
  "--add",
  metavar="a",
  nargs="+",
  help="Path to add to the favorites",
)
parser.add_argument(
  "--remove",
  metavar="r",
  nargs="+",
  help="Path to remove from the favorites",
)
parser.add_argument(
  "--kill",
  metavar="k",
  action="store_const",
  const=True,
  help="Performs killall Finder and sharedfilelistd",
)
args = parser.parse_args();
add_items = []
remove_items = []
if args.add:
  add_items = args.add
  print "Adding items:", add_items
if args.remove:
  remove_items = args.remove
  print "Removing items:", remove_items

def get_users():
  "Get users with a home directory in /Users"

  # get users from dscl
  dscl_users = subprocess.check_output(["/usr/bin/dscl", ".", "-list", "/Users"]).splitlines()

  # get home directories
  homedir_users = os.listdir("/Users")

  # return users that are in both lists
  users = set(dscl_users).intersection(set(homedir_users))
  return [u.strip() for u in users if u.strip() != ""]

def set_favorites(user, add_items, remove_items):
  "Set the Server Favorites for the given user"

  # read existing favorites file
  data = Foundation.NSKeyedUnarchiver.unarchiveObjectWithFile_(favorites_path.format(user=user))
  # reformat add_items to [(name, path), ...]
  new_add_items = []
  for s in add_items:
    new_add_items.append((s, s))

  add_items = new_add_items
  existing_items = []
  # read existing items safely
  if data is not None:
    data_items = data.get("items", [])
    # read existing servers
    for item in data_items:
      # name = item["Name"]
      url, _, _ = Foundation.NSURL.initByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
        Foundation.NSURL.alloc(),
        item["Bookmark"],
        Foundation.NSURLBookmarkResolutionWithoutUI,
        None,
        None,
        None,
      )
      unicode_url = unicode(url)
      if unicode_url != "None":
        existing_items.append((unicode_url, item))

  # get unique ordered list of all items
  all_items = []
  # add existing_items to list, updating name if necessary
  for s in existing_items:
    try:
      idx = [a[1] for a in add_items].index(s[1])
      all_items.append((add_items[idx][0], s[1]))
    except ValueError:
      all_items.append(s)
  # Add items from 'add_items' array
  for s in add_items:
    if s[0] not in [e[0] for e in existing_items]:
      item = {}
      # use unicode to translate to NSString
      url = Foundation.NSURL.URLWithString_(unicode(s[0]))
      bookmark, _ = url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(0, None, None, None)
      item["Bookmark"] = bookmark
      # generate a new UUID for each server
      item["uuid"] = unicode(uuid.uuid1()).upper()
      item["visibility"] = 0
      item["CustomItemProperties"] = Foundation.NSDictionary.new()
      item_to_append = Foundation.NSDictionary.dictionaryWithDictionary_(item)
      all_items.append((unicode(s[0]), item_to_append))

  # Remove items from 'remove_items' array
  all_items = [s for s in all_items if s[0] not in remove_items]


  # Set items:
  items = [s[1] for s in all_items]
  data = Foundation.NSDictionary.dictionaryWithDictionary_({
    "items": Foundation.NSArray.arrayWithArray_(items),
    "properties": Foundation.NSDictionary.dictionaryWithDictionary_({"com.apple.LSSharedFileList.ForceTemplateIcons": False})
  })

  # Write sfl2 file
  Foundation.NSKeyedArchiver.archiveRootObject_toFile_(data, favorites_path.format(user=user))

# loop through users and set favorites
if __name__ == "__main__":
  # if running as root, run for all users. Otherwise run for current user
  user = getpass.getuser()
  if user == "root":
    users = get_users()
  else:
    users = [user]

  for user in users:
    try:
      set_favorites(user, add_items, remove_items)
      # fix owner if ran as root
      if user == "root":
          os.system(("chown {user} " + favorites_path).format(user=user))
      print "FavoriteItems set for " + user
    except Exception as e:
      # if there's an error, log it an continue on
      print "Failed setting FavoriteItems for {0}".format(user)
      print e
  if args.kill:
    os.system("killall sharedfilelistd")
    os.system("killall Finder")

sys.exit()
