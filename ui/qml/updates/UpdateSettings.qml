import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Updates 1.0
import "../theme"
import "../components"

SettingsSection {
    title: "Application Updates"
    description: "Stable updates are checked securely. Installer downloads always require your action."
    SettingsRow {
        title: "Current Version"
        description: "Installed MMO Video Studio version"
        Text { text: Updates.currentVersion; color: Theme.colors.textPrimary; font.family: Theme.type.family }
    }
    SettingsRow {
        title: "Automatically Check"
        description: "Checks lightweight update metadata only. It never downloads an installer automatically."
        AppSwitch { checked: Updates.automaticCheck; onToggled: Updates.setAutomaticallyCheck(checked) }
    }
    SettingsRow {
        title: "Channel"
        description: "Beta is not exposed until a real Beta release channel exists."
        Text { text: Updates.channel; color: Theme.colors.textSecondary; font.family: Theme.type.family }
    }
    RowLayout {
        Layout.fillWidth: true
        SecondaryButton { text: "Check for Updates"; enabled: Updates.state !== "checking" && Updates.state !== "downloading"; onClicked: Updates.checkForUpdates() }
        Text { text: Updates.errorMessage; visible: text.length > 0; color: Theme.colors.textSecondary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
