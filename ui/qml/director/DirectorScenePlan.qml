import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var scene
    property var controller
    implicitHeight: 150
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.xs
        RowLayout { Layout.fillWidth: true
            Text { text: (root.scene.order + 1).toString().padStart(2,"0"); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { Layout.fillWidth: true; text: root.scene.title || "Scene"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideRight }
            AppButton { text: root.scene.locked ? "Locked" : "Lock"; compact: true; variant: root.scene.locked ? "secondary" : "ghost"; onClicked: root.controller.updateScenePlan(root.scene.id, root.scene.title, root.scene.targetDurationMs, !root.scene.locked) }
        }
        Text { Layout.fillWidth: true; text: root.scene.purpose || ""; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap; maximumLineCount: 2 }
        RowLayout { Layout.fillWidth: true
            Text { text: (root.scene.targetDurationMs/1000).toFixed(1) + " sec"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Text { text: "• " + (root.scene.transition || "cut"); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            Item { Layout.fillWidth: true }
            StatusBadge { visible: root.scene.userModified; text: "Edited"; status: "warning" }
        }
    }
}
