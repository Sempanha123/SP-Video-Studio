import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
ColumnLayout {
    id: root
    property var collections: []
    signal collectionSelected(string id)
    spacing: Theme.spacing.xs
    Text { text: "Collections"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.weight: Theme.type.semibold }
    AppButton { Layout.fillWidth: true; text: "All Assets"; variant: "ghost"; onClicked: root.collectionSelected("") }
    Repeater { model: root.collections; delegate: AppButton { required property var modelData; Layout.fillWidth: true; text: modelData.name + "  " + modelData.itemCount; variant:"ghost"; onClicked: root.collectionSelected(modelData.id) } }
    Item { Layout.fillHeight: true }
}
