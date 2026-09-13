import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    id: root
    property var candidate: ({})
    property bool isSelected: false

    interactive: true
    selected: root.isSelected
    accessibleName: (candidate.title || "Short")
        + ". Duration " + (Number(candidate.durationMs || 0) / 1000).toFixed(1) + " seconds"
        + ". Source " + String(candidate.sourceType || "unknown")
        + ". Status " + String(candidate.status || "draft").replaceAll("_", " ")
    onClicked: Shorts.selectCandidate(candidate.id || "")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.sm
        spacing: 2
        RowLayout {
            Layout.fillWidth: true
            Text {
                id: candidateTitle
                Layout.fillWidth: true
                text: candidate.title || "Short"
                color: Theme.colors.textPrimary
                font.family: Theme.type.family
                font.pixelSize: Theme.type.bodySmall
                font.weight: Theme.type.semibold
                elide: Text.ElideRight
                ToolTip.visible: candidateTitleHover.hovered && candidateTitle.truncated
                ToolTip.text: candidateTitle.text
                ToolTip.delay: Theme.tooltipDelay
                HoverHandler { id: candidateTitleHover }
            }
            StatusBadge {
                text: candidate.status || "draft"
                status: candidate.status === "outdated" ? "outdated" : "neutral"
            }
        }
        Text {
            text: (Number(candidate.durationMs || 0) / 1000).toFixed(1) + " sec · " + String(candidate.sourceType || "")
            color: Theme.colors.textMuted
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
        }
        Text {
            visible: !!candidate.hook
            Layout.fillWidth: true
            text: candidate.hook || ""
            color: Theme.colors.textSecondary
            font.family: Theme.type.family
            font.pixelSize: Theme.type.caption
            elide: Text.ElideRight
        }
    }
}
