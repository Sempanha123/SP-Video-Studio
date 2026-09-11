import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
    implicitHeight: Math.max(170, Math.min(360, 90 + (controller ? controller.history.length : 0) * 52))
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
        SectionHeader { title:"Recent Exports"; subtitle:"Previous project outputs and reusable settings" }
        ScrollView { Layout.fillWidth:true; Layout.fillHeight:true; clip:true
            ColumnLayout { width: parent.width; spacing: Theme.spacing.xs
                Repeater { model: root.controller ? root.controller.history : []
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth:true; implicitHeight:48; radius:Theme.radius.sm; color:Theme.colors.surfaceAlt
                        RowLayout { anchors.fill:parent; anchors.leftMargin:Theme.spacing.sm; anchors.rightMargin:Theme.spacing.sm; spacing:Theme.spacing.sm
                            ColumnLayout { Layout.fillWidth:true; spacing:0
                                Text { Layout.fillWidth:true; text:modelData.name || "Export"; elide:Text.ElideMiddle; color:modelData.fileMissing ? Theme.colors.textMuted : Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
                                Text { text:(modelData.resolutionText || "") + (modelData.fileMissing ? " • File Missing" : " • "+(modelData.durationText || "")); color:modelData.fileMissing ? Theme.colors.warning : Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
                            }
                            SecondaryButton { text:"Play"; compact:true; enabled:!modelData.fileMissing; onClicked:root.controller.playOutput(modelData.id) }
                            SecondaryButton { text:"Export Again"; compact:true; onClicked:root.controller.exportAgain(modelData.id) }
                            IconButton { iconName:"folder"; tooltip:"Open folder"; enabled:!modelData.fileMissing; onClicked:root.controller.openFolder(modelData.id) }
                            IconButton { iconName:"trash"; tooltip:modelData.fileMissing ? "Remove from history" : "Delete export"; onClicked: { if(modelData.fileMissing) root.controller.removeFromHistory(modelData.id); else root.controller.deleteOutput(modelData.id, false) } }
                        }
                    }
                }
                Text { visible: !root.controller || root.controller.history.length===0; text:"No exports yet."; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
            }
        }
    }
}
