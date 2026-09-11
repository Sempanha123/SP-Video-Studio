import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"

Rectangle {
    property var analysis: ({})
    property string languageName: "English"
    property string saveState: "Saved"
    implicitHeight: 38
    radius: Theme.radius.medium
    color: Theme.colors.surfaceHover
    border.color: Theme.colors.border

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.md
        anchors.rightMargin: Theme.spacing.md
        spacing: Theme.spacing.sm
        Text {
            text: (analysis.metricValue || 0) + " " + ((analysis.metricLabel || "words") === "characters" ? "characters" : "words")
            color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption
        }
        Text { text: "•"; color: Theme.colors.textMuted }
        Text { text: analysis.durationDisplay || "~0 sec"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Text { text: "•"; color: Theme.colors.textMuted }
        Text { text: languageName; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        Item { Layout.fillWidth: true }
        Text {
            text: saveState
            color: saveState === "Save failed" ? Theme.colors.danger : (saveState === "Saved" ? Theme.colors.success : Theme.colors.textMuted)
            font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold
        }
    }
}
