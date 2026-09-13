import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    property var output: controller ? controller.lastOutput : ({})
    signal anotherVersionRequested()
    accessibleName: "Export complete. " + (output.name || "Exported video")
    implicitHeight: 205
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing:2
                Text { text:"Export complete"; color:Theme.colors.success; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
                Text { Layout.fillWidth:true; text:root.output.name || "Exported video"; elide:Text.ElideMiddle; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.body }
            }
            StatusBadge { text:"Completed"; status:"ready" }
        }
        Text { text:(root.output.resolutionText || "") + (root.output.durationText ? " • "+root.output.durationText : "") + (root.output.fileSizeText ? " • "+root.output.fileSizeText : ""); color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
        RowLayout { Layout.fillWidth:true
            AppButton { text:"Play Video"; compact:true; onClicked: if(root.controller && root.output.id) root.controller.playOutput(root.output.id) }
            SecondaryButton { text:"Open File"; compact:true; onClicked: if(root.controller && root.output.id) root.controller.openFile(root.output.id) }
            SecondaryButton { text:"Open Folder"; compact:true; onClicked: if(root.controller && root.output.id) root.controller.openFolder(root.output.id) }
            Item { Layout.fillWidth:true }
            SecondaryButton { text:"Export Another Version"; compact:true; onClicked: root.anotherVersionRequested() }
        }
    }
}
