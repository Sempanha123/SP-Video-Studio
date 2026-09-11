import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ColumnLayout {
    id: root
    required property var controller
    spacing: Theme.spacing.lg

    StorageOverview { Layout.fillWidth: true; controller: root.controller }

    RowLayout {
        Layout.fillWidth: true; spacing: Theme.spacing.md
        Text { text: "Storage Breakdown"; Layout.fillWidth: true; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        SecondaryButton { text: "Clear Cache"; compact: true; onClicked: cleanup.open() }
        SecondaryButton { text: "Cache Location"; compact: true; onClicked: location.open() }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: width < 760 ? 1 : 2
        columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.md
        Repeater {
            model: root.controller.categories
            delegate: StorageCategoryCard {
                required property var modelData
                Layout.fillWidth: true
                title: modelData.label
                sizeText: modelData.sizeDisplay
                safety: modelData.safety
                description: modelData.safety === "safe_to_clear" ? "Safe temporary files that can be recreated." : (modelData.safety === "regeneratable" ? "Rebuildable data; referenced project content stays protected." : (modelData.safety === "protected" ? "Protected data managed by its dedicated feature." : (modelData.safety === "external" ? "Referenced outside app storage; not counted as owned usage." : "User/project files are never cleared automatically.")))
                manageable: modelData.safety === "safe_to_clear" || modelData.safety === "regeneratable"
                onManageRequested: { selectedCleanup.selectedCategories=[modelData.category]; selectedCleanup.open() }
            }
        }
    }

    ProjectStorageList { Layout.fillWidth: true; controller: root.controller }

    SettingsSection {
        Layout.fillWidth: true
        title: "Cache Settings"
        description: "Balanced cleanup removes stale safe cache and enforces the size limit. Protected data is always excluded."
        SettingsRow {
            title: "Maximum Cache Size"
            description: root.controller.preferences.maximumCacheDisplay || "25 GB"
            ColumnLayout {
                spacing: Theme.spacing.xs
                AppComboBox {
                    id: maxCacheCombo
                    Layout.preferredWidth: 170
                    model: ["10 GB","25 GB","50 GB","100 GB","Unlimited","Custom"]
                    onActivated: {
                        if (currentText === "Custom") return
                        var value=currentText === "Unlimited" ? 0 : parseFloat(currentText)
                        root.controller.setMaximumCacheGB(value)
                    }
                }
                AppTextField {
                    Layout.preferredWidth: 170
                    visible: maxCacheCombo.currentText === "Custom"
                    placeholderText: "Custom GB"
                    validator: DoubleValidator { bottom: 1 }
                    onEditingFinished: {
                        var value=parseFloat(text)
                        if (!isNaN(value) && value > 0) root.controller.setMaximumCacheGB(value)
                    }
                }
            }
        }
        SettingsRow {
            title: "Automatic Cleanup"
            description: "Conservative cleans stale temp and old logs. Balanced also applies the cache limit with LRU."
            AppComboBox { Layout.preferredWidth: 170; model: ["Off","Conservative","Balanced"]; onActivated: root.controller.setAutomaticCleanup(currentText) }
        }
        SettingsRow { title: "Cleanup stale temp files"; AppSwitch { checked: root.controller.preferences.cleanupStaleTemp !== false; onToggled: root.controller.setCleanupStaleTemp(checked) } }
        SettingsRow {
            title: "Log Retention"
            description: "Keep recent diagnostic logs; the current active log is never removed."
            RowLayout {
                AppComboBox { Layout.preferredWidth: 120; model: ["7 days","14 days","30 days","60 days"]; onActivated: root.controller.setLogRetentionDays(parseInt(currentText)) }
                SecondaryButton { text: "Clear Old Logs"; compact: true; onClicked: root.controller.clearOldLogs() }
            }
        }
    }

    CleanupDialog { id: cleanup; controller: root.controller; clearAll: true; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2 }
    CleanupDialog { id: selectedCleanup; controller: root.controller; clearAll: false; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2 }
    CacheLocationDialog { id: location; controller: root.controller; parent: Overlay.overlay; x: (parent.width-width)/2; y: (parent.height-height)/2 }
}
