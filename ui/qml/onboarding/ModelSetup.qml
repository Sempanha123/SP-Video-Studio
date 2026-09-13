import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Onboarding 1.0
import "../theme"
import "../components"

SetupStep {
    id: root
    title: "AI features are optional"
    description: "MMO Video Studio can work manually without AI models. Install only the features you want; nothing is downloaded automatically."
    Component.onCompleted: if (!Onboarding.discoveringModels && Onboarding.models.length === 0) Onboarding.refreshModels()
    GridLayout {
        Layout.fillWidth: true; columns: width < 700 ? 1 : 3; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.md
        AppCard { Layout.fillWidth: true; implicitHeight: 150
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md
                Text { text: "Voice Generation"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Text { text: "VoxCPM2"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                StatusBadge { text: Onboarding.readiness.voxcpmStatus === "installed" ? "Installed" : "Not Installed"; status: Onboarding.readiness.voxcpmStatus === "installed" ? "ready" : "warning" }
                Item { Layout.fillHeight: true }
                SecondaryButton { text: "Install / Manage"; onClicked: Onboarding.openModels() }
            }
        }
        AppCard { Layout.fillWidth: true; implicitHeight: 150
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md
                Text { text: "Speech Recognition"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Text { text: "faster-whisper"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                StatusBadge { text: Onboarding.readiness.whisperStatus === "installed" ? "Installed" : "Not Installed"; status: Onboarding.readiness.whisperStatus === "installed" ? "ready" : "warning" }
                Item { Layout.fillHeight: true }
                SecondaryButton { text: "Install / Manage"; onClicked: Onboarding.openModels() }
            }
        }
        AppCard { Layout.fillWidth: true; implicitHeight: 150
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md
                Text { text: "Translation"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                Text { text: "Configured translation engines"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                StatusBadge { text: "Optional"; status: "warning" }
                Item { Layout.fillHeight: true }
                SecondaryButton { text: "Open Models"; onClicked: Onboarding.openModels() }
            }
        }
    }
    Text { text: "Performance profile"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
    AppComboBox { Layout.preferredWidth: 240; model: ["Auto","Low Memory","Balanced","Maximum Quality"]; Component.onCompleted: currentIndex = Math.max(0,["auto","low_memory","balanced","maximum_quality"].indexOf(Onboarding.performanceProfile)); onActivated: Onboarding.setPerformanceProfile(["auto","low_memory","balanced","maximum_quality"][currentIndex]) }
    InfoBanner { Layout.fillWidth: true; text: "Auto lets MMO Video Studio choose safe performance settings for this computer. Local projects and local models stay on this computer unless you use a configured online provider." }
    RowLayout { Layout.fillWidth: true
        AppButton { text: "Continue Without AI"; accessibleName: "Continue without AI models"; onClicked: Onboarding.continueWithoutAI() }
        Item { Layout.fillWidth: true }
    }
}
