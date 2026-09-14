import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Updates 1.0
import "../theme"
import "../components"

AppDialog {
    id: dialog
    width: 520
    header: null
    footer: null
    contentItem: ColumnLayout {
        spacing: Theme.spacing.lg
        Text { text: "MMO Video Studio " + Updates.availableVersion + " is available."; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        Text { text: "Current: " + Updates.currentVersion; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        Text { Layout.fillWidth: true; visible: Updates.releaseNotes.length > 0; text: Updates.releaseNotes; wrapMode: Text.WordWrap; textFormat: Text.PlainText; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        UpdateProgress { Layout.fillWidth: true; visible: Updates.state === "downloading" || Updates.state === "validating" }
        Text { Layout.fillWidth: true; visible: Updates.activeWorkMessage.length > 0; text: Updates.activeWorkMessage; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        Text { Layout.fillWidth: true; visible: Updates.errorMessage.length > 0; text: Updates.errorMessage; wrapMode: Text.WordWrap; textFormat: Text.PlainText; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        RowLayout {
            Layout.fillWidth: true
            SecondaryButton { text: "View Changes"; visible: Updates.releaseNotesUrl.length > 0; onClicked: Updates.openReleaseNotes() }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Later"; onClicked: dialog.close() }
            AppButton { text: Updates.installReady ? "Install Now" : "Download Update"; enabled: !Updates.installReady || Updates.activeWorkMessage.length === 0; onClicked: Updates.installReady ? Updates.installNow() : Updates.downloadUpdate() }
        }
    }
}
