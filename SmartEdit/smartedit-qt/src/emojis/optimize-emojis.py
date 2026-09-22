from classes import info
import os
import json

REMOVE_GROUPS = ['flags', 'extras-unicode', 'component', 'people-body']
REMOVE_SUBGROUPS = ['alphanum', 'keycap', 'transport-sign', 'religion,', 'animals-nature', 'climate-environment',
                    'emergency', 'flags', 'food-drink', 'gardening', 'healthcare', 'objects', 'people',
                    'smileys-emotion', 'symbol-other', 'symbols', 'technology', 'travel-places']



emoji_metadata_path = os.path.join(info.PATH, "emojis", "data", "openmoji.json")
with open(emoji_metadata_path, 'r', encoding="utf-8") as f:
    emoji_metadata = json.load(f)


emoji_lookup = {}
for emoji in emoji_metadata:
    if emoji.get('group') not in REMOVE_GROUPS and emoji.get('subgroups') not in REMOVE_SUBGROUPS:
        emoji_lookup[emoji.get("hexcode")] = emoji


emoji_removed_count = 0
emoji_file_path = os.path.join(info.PATH, "emojis", "color", "svg")
for filename in os.listdir(emoji_file_path):
    fileBaseName = os.path.splitext(filename)[0]
    emoji = emoji_lookup.get(fileBaseName, {})
    if not emoji:
        
        emoji_path = os.path.join(emoji_file_path, filename)
        os.unlink(emoji_path)
        emoji_removed_count += 1
        print('Removed emoji: %s' % emoji_path)


emoji_metadata_optimized_path = os.path.join(info.PATH, "emojis", "data", "openmoji-optimized.json")
with open(emoji_metadata_optimized_path, 'w', encoding='utf-8') as file:
    file.write(json.dumps(emoji_lookup))

print('Emojis Optimized (%s removed)!' % emoji_removed_count)
