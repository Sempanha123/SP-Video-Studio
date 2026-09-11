import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase23 1.0
import "../theme"
import "../components"

AppCard {
    id: root
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm

        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Short Settings"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.headingSmall; font.weight: Theme.type.semibold }
            Text { text: "9:16 recommended"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: Theme.spacing.xs
            columnSpacing: Theme.spacing.sm

            Text { text: "Duration"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: duration; Layout.fillWidth: true; model: ["15 sec", "30 sec", "45 sec", "60 sec", "90 sec"]; currentIndex: 1 }

            Text { text: "Aspect"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: aspect; Layout.fillWidth: true; model: ["9:16", "1:1", "16:9"] }

            Text { text: "Platform"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: platform; Layout.fillWidth: true; model: ["Generic", "TikTok", "YouTube Shorts", "Instagram Reels", "Facebook"] }

            Text { text: "Language"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            LanguagePicker { id: language; Layout.fillWidth: true; currentCode: String(Shorts.settings.language || "en") }

            Text { text: "Style"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: style; Layout.fillWidth: true; model: ["Creator", "Clean", "News", "Documentary", "Minimal"] }
        }

        AppButton {
            Layout.fillWidth: true
            text: "Save Short Settings"
            onClicked: {
                var durations = [15000, 30000, 45000, 60000, 90000]
                var platforms = ["generic", "tiktok", "youtube_shorts", "instagram_reels", "facebook"]
                Shorts.updateSettings(durations[duration.currentIndex], aspect.currentText, language.currentCode || "en", platforms[platform.currentIndex], style.currentText.toLowerCase())
            }
        }
    }
}
