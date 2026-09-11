import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property string section: "Appearance"
    RowLayout { anchors.fill: parent; spacing: Theme.spacing.xl
        AppCard {
            Layout.preferredWidth: 210; Layout.fillHeight: true
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.xs
                Text { text: "Settings"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold; Layout.leftMargin: Theme.spacing.sm; Layout.topMargin: Theme.spacing.sm; Layout.bottomMargin: Theme.spacing.sm }
                Repeater { model: ["General", "Appearance", "Projects", "Performance", "Rendering", "Storage", "Advanced"]
                    delegate: SidebarItem { required property string modelData; Layout.fillWidth: true; text: modelData; iconName: modelData === "Appearance" ? "theme" : "settings"; selected: root.section === modelData; onClicked: root.section = modelData }
                }
                Item { Layout.fillHeight: true }
            }
        }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
            ColumnLayout { width: parent.width; spacing: Theme.spacing.xl
                ColumnLayout { Layout.fillWidth: true; spacing: 2
                    Text { text: root.section; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                    Text { text: root.section === "Appearance" ? "Choose how SP Video Studio looks on your desktop." : "This settings category is prepared for a later phase."; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                }
                AppCard { visible: root.section === "Appearance"; Layout.fillWidth: true; Layout.preferredHeight: 220
                    ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.xl; spacing: Theme.spacing.lg
                        Text { text: "Theme"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        ButtonGroup { id: themeGroup }
                        RadioButton { text: "System"; checked: Theme.mode === "system"; ButtonGroup.group: themeGroup; onClicked: Theme.setMode("system"); palette.text: Theme.colors.textPrimary }
                        RadioButton { text: "Light"; checked: Theme.mode === "light"; ButtonGroup.group: themeGroup; onClicked: Theme.setMode("light"); palette.text: Theme.colors.textPrimary }
                        RadioButton { text: "Dark"; checked: Theme.mode === "dark"; ButtonGroup.group: themeGroup; onClicked: Theme.setMode("dark"); palette.text: Theme.colors.textPrimary }
                    }
                }
                AppCard { visible: root.section !== "Appearance"; Layout.fillWidth: true; Layout.preferredHeight: 230; EmptyState { anchors.centerIn: parent; title: root.section + " settings"; description: "The settings shell is ready. Functional controls for this category arrive in its dedicated phase."; iconName: "settings" } }
                Item { Layout.fillHeight: true }
            }
        }
    }
}
