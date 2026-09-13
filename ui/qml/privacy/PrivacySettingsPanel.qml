import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Privacy 1.0
import "../theme"
import "../components"

ColumnLayout {
    id: root
    spacing: Theme.spacing.lg
    signal navigateRequested(string page, string context)

    SettingsSection {
        Layout.fillWidth: true
        title: "Local & Online Processing"
        description: "See which current actions stay on this device and which explicitly use the network."
        Repeater {
            model: Privacy.providerRows
            delegate: SettingsRow {
                required property var modelData
                title: modelData.name
                description: modelData.detail
                RowLayout {
                    spacing: Theme.spacing.sm
                    StatusBadge { text: modelData.mode; status: modelData.online ? "warning" : "ready" }
                    StatusBadge { visible: !modelData.configured; text: "Not configured"; status: "unknown" }
                }
            }
        }
    }

    SettingsSection {
        Layout.fillWidth: true
        title: "Private Data Handling"
        description: "Privacy boundaries for diagnostics, support files and sensitive voice media."
        InfoBanner { Layout.fillWidth: true; text: Privacy.summary.diagnostics }
        InfoBanner { Layout.fillWidth: true; text: Privacy.summary.supportBundle }
        InfoBanner { Layout.fillWidth: true; text: Privacy.summary.referenceVoices }
        InfoBanner { Layout.fillWidth: true; text: Privacy.summary.localWorkflow }
    }

    SettingsSection {
        Layout.fillWidth: true
        title: "Review & Cleanup"
        description: "Use the existing storage, diagnostics and voice tools. Security failures never delete project data automatically."
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spacing.sm
            SecondaryButton { text: "Storage Cleanup"; onClicked: root.navigateRequested("settings", "Storage") }
            SecondaryButton { text: "Diagnostics"; onClicked: root.navigateRequested("diagnostics", "") }
            SecondaryButton { text: "Manage Voices"; onClicked: root.navigateRequested("voices", "") }
            Item { Layout.fillWidth: true }
        }
    }

    InfoBanner {
        Layout.fillWidth: true
        variant: "warning"
        text: "Any future cloud AI provider must clearly explain what project text or audio may leave this device before its first use. No cloud AI provider is configured by Phase 37."
    }
}
