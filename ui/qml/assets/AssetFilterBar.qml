import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
RowLayout {
    id: root
    signal queryChanged(string value); signal filterChanged(string value); signal sortChanged(string value)
    spacing: Theme.spacing.sm
    Timer { id: searchDebounce; interval: 220; repeat: false; onTriggered: root.queryChanged(search.text) }
    SearchField {
        id: search; Layout.fillWidth: true; placeholderText: "Search names, tags, collections…"
        onTextChanged: searchDebounce.restart()
        onClearRequested: { searchDebounce.stop(); root.queryChanged("") }
    }
    AppComboBox { Layout.preferredWidth: 150; model: ["All","Video","Image","Audio","Favorites","Green Screen","Presenter","Reporter","B-roll","Music","SFX","Missing","Unused"]; onCurrentTextChanged: root.filterChanged(currentText.toLowerCase().replaceAll(" ","-").replace("b-roll","broll")) }
    AppComboBox { Layout.preferredWidth: 154; model: ["Recently Added","Recently Used","Name","Duration","File Size"]; onCurrentTextChanged: root.sortChanged(currentText.toLowerCase().replaceAll(" ","_")) }
}
