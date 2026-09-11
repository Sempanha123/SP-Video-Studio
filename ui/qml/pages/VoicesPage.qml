import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    ScrollView { anchors.fill: parent; clip: true; contentWidth: availableWidth
        ColumnLayout { width: parent.width; spacing: Theme.spacing.xl
            ColumnLayout { Layout.fillWidth: true; spacing: 2
                Text { text: "Voices"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                Text { text: "Explore the voice library structure before synthesis engines are connected."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body }
            }
            SectionHeader { title: "Preset Voices"; Layout.fillWidth: true }
            GridLayout { Layout.fillWidth: true; columns: width < 780 ? 1 : 2; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
                VoiceCard { Layout.fillWidth: true; voiceName: "Alex"; styleName: "News Anchor"; language: "English" }
                VoiceCard { Layout.fillWidth: true; voiceName: "Maya"; styleName: "Storyteller"; language: "English" }
            }
            SectionHeader { title: "Designed Voices"; Layout.fillWidth: true }
            GridLayout { Layout.fillWidth: true; columns: width < 780 ? 1 : 2; columnSpacing: Theme.spacing.lg; rowSpacing: Theme.spacing.lg
                VoiceCard { Layout.fillWidth: true; voiceName: "Harbor"; styleName: "Documentary"; language: "English" }
                VoiceCard { Layout.fillWidth: true; voiceName: "Soriya"; styleName: "Professional"; language: "Khmer" }
            }
            SectionHeader { title: "My Voices"; Layout.fillWidth: true }
            AppCard { Layout.fillWidth: true; Layout.preferredHeight: 150; EmptyState { anchors.centerIn: parent; title: "No personal voices yet"; description: "User-owned reference voices will be managed here in a later phase."; iconName: "mic" } }
        }
    }
}
