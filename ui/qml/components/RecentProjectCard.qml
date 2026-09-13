import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property var projectData: ({})
    signal openRequested(string projectId)
    interactive: true
    accessibleName: (root.projectData.title || "Untitled Project") + ". " + (root.projectData.workflowName || "Video") + ". Last activity " + (root.projectData.lastActivityDisplay || "Never")
    implicitHeight: Math.max(74, Math.round(74 * Theme.textScale))
    onClicked: root.openRequested(root.projectData.id)

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.md
        Rectangle {
            width: 42; height: 42; radius: Theme.radius.medium
            color: Theme.colors.surfaceHover
            Icon { anchors.centerIn: parent; width: 20; height: 20; name: "projects" }
        }
        ColumnLayout {
            Layout.fillWidth: true; spacing: 1
            Text {
                id: projectTitle
                Layout.fillWidth: true
                text: root.projectData.title || "Untitled Project"
                color: Theme.colors.textPrimary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.body
                font.weight: Theme.type.semibold
                elide: Text.ElideRight
                ToolTip.visible: projectTitleHover.hovered && projectTitle.truncated
                ToolTip.text: projectTitle.text
                ToolTip.delay: Theme.tooltipDelay
                HoverHandler { id: projectTitleHover }
            }
            Text {
                Layout.fillWidth: true
                text: (root.projectData.workflowName || "Video") + " · " + (root.projectData.lastActivityDisplay || "Never")
                color: Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
                elide: Text.ElideRight
            }
        }
        Icon { width: 16; height: 16; name: "arrow-right" }
    }
}
