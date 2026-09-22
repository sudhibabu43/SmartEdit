class NameColumnKeyboardSearchMixin:
    """Run Qt's incremental keyboard search against the visible name column."""

    keyboard_search_column = 1

    def keyboardSearch(self, search):
        model = self.model()
        current = self.currentIndex()
        if model and model.rowCount() > 0:
            if current.isValid():
                name_index = current.sibling(current.row(), self.keyboard_search_column)
            else:
                name_index = model.index(0, self.keyboard_search_column)
            if name_index.isValid():
                self.setCurrentIndex(name_index)
        super().keyboardSearch(search)
