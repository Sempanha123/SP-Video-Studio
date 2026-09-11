import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var translation: ({})
    implicitHeight: 92
    RowLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.lg
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Text { text: (root.translation.sourceLanguageName || "Source") + " → " + (root.translation.targetLanguageName || "Target"); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            Text { text: "Provider: " + ((root.translation.engine_id || "manual") === "manual" ? "Manual Translation" : "Local Translation"); color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        ColumnLayout { spacing: 2; Text { text: "Review"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }; Text { text: Math.round((root.translation.reviewProgress || 0) * 100) + "%"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body } }
    }
}
