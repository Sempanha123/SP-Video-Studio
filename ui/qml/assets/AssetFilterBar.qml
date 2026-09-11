import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
RowLayout {
    id: root
    signal queryChanged(string value); signal filterChanged(string value); signal sortChanged(string value)
    spacing: Theme.spacing.sm
    AppTextField { Layout.fillWidth: true; placeholderText: "Search names, tags, collections…"; onTextChanged: root.queryChanged(text) }
    AppComboBox { model: ["All","Video","Image","Audio","Favorites","Green Screen","Presenter","Reporter","B-roll","Music","SFX","Missing","Unused"]; onCurrentTextChanged: root.filterChanged(currentText.toLowerCase().replaceAll(" ","-").replace("b-roll","broll")) }
    AppComboBox { model: ["Recently Added","Recently Used","Name","Duration","File Size"]; onCurrentTextChanged: root.sortChanged(currentText.toLowerCase().replaceAll(" ","_")) }
}
