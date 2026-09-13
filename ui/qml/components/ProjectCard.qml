import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

AppCard {
    id: root
    property var projectData: ({})
    signal openRequested(string projectId)
    signal renameRequested(string projectId, string title)
    signal duplicateRequested(string projectId)
    signal deleteRequested(string projectId, string title)

    accessibleName: (root.projectData.title || "Untitled Project") + ". " + (root.projectData.workflowName || "Video") + ". " + (root.projectData.languageName || "English") + ". " + (root.projectData.statusName || "Draft")
    implicitHeight: Math.max(122, Math.round(122 * Theme.textScale))

    RowLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.lg
        spacing: Theme.spacing.lg

        Rectangle {
            Layout.preferredWidth: 64
            Layout.preferredHeight: 64
            radius: Theme.radius.large
            color: Theme.colors.surfaceHover
            Icon { anchors.centerIn: parent; width: 28; height: 28; name: "projects" }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            RowLayout {
                Layout.fillWidth: true
                Text {
                    id: projectTitleLabel
                    Layout.fillWidth: true
                    text: root.projectData.title || "Untitled Project"
                    color: Theme.colors.textPrimary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.heading
                    font.weight: Theme.type.semibold
                    elide: Text.ElideRight
                    ToolTip.visible: projectTitleHover.hovered && projectTitleLabel.truncated
                    ToolTip.text: text
                    ToolTip.delay: Theme.tooltipDelay
                    HoverHandler { id: projectTitleHover }
                }
                StatusBadge {
                    text: root.projectData.statusName || "Draft"
                    status: root.projectData.status === "completed" ? "completed" : "offline"
                }
            }
            Text {
                Layout.fillWidth: true
                text: (root.projectData.workflowName || "Video") + "  ·  " +
                      (root.projectData.languageName || "English") + "  ·  " +
                      (root.projectData.aspectRatio || "16:9") + "  ·  " +
                      (root.projectData.fps || 30) + " FPS"
                color: Theme.colors.textSecondary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.bodySmall
                elide: Text.ElideRight
            }
            Text {
                text: "Last activity " + (root.projectData.lastActivityDisplay || "Never")
                color: Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
            }
        }

        RowLayout {
            spacing: Theme.spacing.xs
            AppButton {
                text: "Open"
                compact: true
                iconName: "open"
                onClicked: root.openRequested(root.projectData.id)
            }
            IconButton {
                iconName: "edit"
                tooltip: "Rename"
                onClicked: root.renameRequested(root.projectData.id, root.projectData.title)
            }
            IconButton {
                iconName: "copy"
                tooltip: "Duplicate"
                onClicked: root.duplicateRequested(root.projectData.id)
            }
            IconButton {
                iconName: "trash"
                accessibleName: "Delete project"
                tooltip: "Delete Project"
                onClicked: root.deleteRequested(root.projectData.id, root.projectData.title)
            }
        }
    }
}
