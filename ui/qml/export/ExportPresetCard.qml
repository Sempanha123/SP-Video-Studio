import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var preset: ({})
    property bool selected: false
    signal chosen()
    signal duplicateRequested()
    signal deleteRequested()
    implicitWidth: 210
    implicitHeight: 142
    border.color: selected ? Theme.colors.accent : Theme.colors.border
    border.width: selected ? 2 : 1

    MouseArea { anchors.fill: parent; onClicked: root.chosen() }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.xs
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: root.preset.name || "Preset"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideRight }
            StatusBadge { text: root.preset.builtin ? "Built in" : "Custom"; status: root.preset.builtin ? "ready" : "draft" }
        }
        Text { text: (root.preset.aspectRatio || "") + "  •  " + (root.preset.width || 0) + " × " + (root.preset.height || 0); color: Theme.colors.accent; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        Text { Layout.fillWidth: true; Layout.fillHeight: true; text: root.preset.description || ""; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        RowLayout {
            Layout.fillWidth: true
            Text { text: (root.preset.fps || 30) + " FPS"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
            IconButton { iconName: "copy"; tooltip: "Duplicate preset"; onClicked: root.duplicateRequested() }
            IconButton { visible: !root.preset.builtin; iconName: "trash"; tooltip: "Delete custom preset"; onClicked: root.deleteRequested() }
        }
    }
}
