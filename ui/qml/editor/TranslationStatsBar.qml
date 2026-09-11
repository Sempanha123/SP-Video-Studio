import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Rectangle {
    id: root
    property var translation: ({})
    property string saveState: "Saved"
    implicitHeight: 42
    radius: Theme.radius.medium
    color: Theme.colors.surface
    border.color: Theme.colors.border

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacing.md
        anchors.rightMargin: Theme.spacing.md
        spacing: Theme.spacing.md
        Text { text: (root.translation.sourceLanguageName || "—") + " → " + (root.translation.targetLanguageName || "—"); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; font.weight: Theme.type.semibold }
        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 18; color: Theme.colors.border }
        Text { text: "Reviewed " + (root.translation.reviewProgressText || "0 / 0"); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        ProgressBar { Layout.preferredWidth: 120; from: 0; to: 1; value: root.translation.reviewProgress || 0 }
        Item { Layout.fillWidth: true }
        Text { text: root.saveState; color: root.saveState === "Save Failed" ? Theme.colors.danger : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        StatusBadge { text: root.translation.statusName || "Draft"; status: (root.translation.status || "draft") === "approved" ? "ready" : ((root.translation.status || "") === "outdated" ? "warning" : "unknown") }
    }
}
