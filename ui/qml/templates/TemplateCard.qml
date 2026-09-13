import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var templateData: ({})
    signal selected(string templateId)
    signal useRequested(string templateId)

    implicitHeight: Math.max(218, Math.round(218 * Theme.textScale))
    interactive: true
    accessibleName: (templateData.name || "Template") + ". "
        + (templateData.category || "General") + ". Aspect ratios "
        + ((templateData.aspects || [templateData.aspect || "16:9"]).join(", "))
        + ((templateData.features || []).length
            ? ". Features " + (templateData.features || []).slice(0, 3).join(", ")
            : "")
    onClicked: root.selected(templateData.id || "")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.sm
        spacing: Theme.spacing.sm

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 92
            radius: Theme.radius.medium
            color: Theme.colors.previewBackground
            clip: true
            Accessible.name: "Template preview for " + (templateData.name || "Template")
            Accessible.role: Accessible.Graphic

            Rectangle {
                anchors.centerIn: parent
                width: 44; height: 44; radius: 13
                color: Theme.colors.accentSoft
                Icon {
                    anchors.centerIn: parent
                    width: 21; height: 21
                    name: templateData.workflow === "news" ? "news"
                        : templateData.workflow === "story" ? "story"
                        : templateData.workflow === "shorts" ? "shorts"
                        : "template"
                }
            }
            StatusBadge {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 8
                text: templateData.aspect || ((templateData.aspects || ["16:9"])[0])
                status: "neutral"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Text {
                    id: templateTitle
                    Layout.fillWidth: true
                    text: templateData.name || "Template"
                    color: Theme.colors.textPrimary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.bodyStrong
                    font.weight: Theme.type.semibold
                    elide: Text.ElideRight
                    ToolTip.visible: templateTitleHover.hovered && templateTitle.truncated
                    ToolTip.text: templateTitle.text
                    ToolTip.delay: Theme.tooltipDelay
                    HoverHandler { id: templateTitleHover }
                }
                Text {
                    Layout.fillWidth: true
                    text: (templateData.category || "General") + " · " + (templateData.builtin ? "Built-in" : "My template")
                    color: Theme.colors.textMuted
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.caption
                    elide: Text.ElideRight
                }
            }
            AppButton {
                text: "Use Template"
                size: "small"
                accessibleName: "Use " + (templateData.name || "template")
                onClicked: root.useRequested(templateData.id || "")
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: 5
            Repeater {
                model: (templateData.features || []).slice(0, 3)
                delegate: StatusBadge {
                    required property var modelData
                    text: String(modelData).replaceAll("_", " ")
                    status: "info"
                }
            }
        }
    }
}
