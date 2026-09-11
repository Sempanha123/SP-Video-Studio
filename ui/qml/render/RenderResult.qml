import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var output: controller ? controller.lastOutput : ({})
    implicitHeight: 185
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Video Ready"; color: Theme.colors.success; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                Text { text: root.output.name || "Rendered video"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; elide: Text.ElideMiddle; Layout.fillWidth: true }
            }
            StatusBadge { text: "Completed"; status: "ready" }
        }
        Text { text: (root.output.resolutionText || "") + (root.output.durationText ? " • " + root.output.durationText : "") + (root.output.fileSizeText ? " • " + root.output.fileSizeText : ""); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        RowLayout { Layout.fillWidth: true
            AppButton { text: "Play"; compact: true; onClicked: if (root.controller && root.output.id) root.controller.playOutput(root.output.id) }
            SecondaryButton { text: "Open Folder"; compact: true; onClicked: if (root.controller && root.output.id) root.controller.openFolder(root.output.id) }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Render Again"; compact: true; onClicked: if (root.controller) root.controller.retryLast() }
        }
    }
}
