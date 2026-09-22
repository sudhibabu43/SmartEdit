import pickle
import json
from qt_api import QMimeData
from classes.query import QueryObject


class ClipboardManager:
    """ Manages clipboard operations for QueryObjects or lists of QueryObjects """

    @staticmethod
    def to_mime(data):
        """
        Converts QueryObject or list of QueryObjects to QMimeData.
        Handles both JSON (for text) and pickled formats.
        """
        mime_data = QMimeData()

        
        if isinstance(data, list) and len(data) == 1:
            data = data[0]

        try:
            
            json_data = {}
            if isinstance(data, QueryObject):
                json_data = json.dumps(data.data, indent=4)
            
            elif isinstance(data, list) and all(isinstance(obj, QueryObject) for obj in data):
                json_data = json.dumps([obj.data for obj in data], indent=4)

            
            pickled_data = pickle.dumps(data)

            
            mime_data.setText(json_data)

            
            mime_data.setData(f"application/x-smartedit-generic", pickled_data)

        except (TypeError, AttributeError) as e:
            print(f"Error serializing data: {e}")

        return mime_data

    @staticmethod
    def from_mime(mime_data):
        """
        Converts QMimeData back into the original object (QueryObject or list of QueryObjects).
        Assumes the data is pickled.
        """
        if mime_data.hasFormat("application/x-smartedit-generic"):
            try:
                pickled_data = mime_data.data("application/x-smartedit-generic").data()
                return pickle.loads(pickled_data)
            except (pickle.UnpicklingError, AttributeError) as e:
                print(f"Error unpickling data: {e}")

        print("No valid SmartEdit MIME type found.")
        return None
