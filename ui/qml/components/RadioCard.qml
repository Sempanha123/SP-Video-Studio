import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
AppCard {
    id: root
    property string title: ""
    property string description: ""
    property string value: ""
    signal chosen(string value)
    interactive: true
    accessibleName: title + (description.length > 0 ? ". " + description : "")
    Accessible.role: Accessible.RadioButton
    Accessible.checked: selected
    implicitHeight: Math.max(72, 72 * Theme.textScale)
    onClicked: chosen(value)
    RowLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.md
        Rectangle { width: 18; height: 18; radius: 9; color: "transparent"; border.width: root.selected ? 5 : 2; border.color: root.selected ? Theme.colors.accent : Theme.colors.borderStrong }
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Text { text: root.title; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.medium }
            Text { text: root.description; visible: root.description.length > 0; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; wrapMode: Text.WordWrap; Layout.fillWidth: true; lineHeightMode: Text.ProportionalHeight; lineHeight: Theme.type.normalLineHeight }
        }
    }
}
