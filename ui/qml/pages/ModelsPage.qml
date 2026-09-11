import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    signal toastRequested(string message, string variant)
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.xl
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Text { text: "AI Models"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
            Text { text: "Manage local AI engines and their installation state."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
        }
        GridLayout { Layout.fillWidth: true; columns: width < 800 ? 1 : 2; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
            AppCard { Layout.fillWidth: true; Layout.preferredHeight: 156
                ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                    RowLayout { Layout.fillWidth: true; Rectangle { width: 36; height: 36; radius: Theme.radius.medium; color: Theme.colors.accentSoft; Icon { anchors.centerIn: parent; width: 19; height: 19; name: "mic" } }; ColumnLayout { Layout.fillWidth: true; spacing: 1; Text { text: "VoxCPM2"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }; Text { text: "Text-to-Speech"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption } }; StatusBadge { text: "Not Installed"; status: "not-installed" } }
                    Item { Layout.fillHeight: true }
                    RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; AppButton { text: "Install"; compact: true; onClicked: root.toastRequested("Model installation will be available in a later phase.", "info") } }
                }
            }
            AppCard { Layout.fillWidth: true; Layout.preferredHeight: 156
                ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                    RowLayout { Layout.fillWidth: true; Rectangle { width: 36; height: 36; radius: Theme.radius.medium; color: Theme.colors.surfaceHover; Icon { anchors.centerIn: parent; width: 19; height: 19; name: "wave" } }; ColumnLayout { Layout.fillWidth: true; spacing: 1; Text { text: "faster-whisper"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }; Text { text: "Speech-to-Text"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption } }; StatusBadge { text: "Not Installed"; status: "not-installed" } }
                    Item { Layout.fillHeight: true }
                    RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; AppButton { text: "Install"; compact: true; onClicked: root.toastRequested("Model installation will be available in a later phase.", "info") } }
                }
            }
        }
        Item { Layout.fillHeight: true }
    }
}
