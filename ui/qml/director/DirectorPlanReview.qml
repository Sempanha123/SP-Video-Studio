import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    signal applyRequested()
    ScrollView {
        anchors.fill: parent; clip: true
        ColumnLayout {
            width: root.width - 24; spacing: Theme.spacing.lg
            RowLayout { Layout.fillWidth: true
                ColumnLayout { Layout.fillWidth: true; spacing: 2
                    Text { text: (root.controller.plan.platform || "Production Plan").replace(/_/g," ").toUpperCase(); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    Text { text: ((root.controller.plan.targetDurationMs || 0)/1000).toFixed(0) + " sec • " + (root.controller.plan.aspectRatio || "16:9") + " • " + root.controller.scenePlans.length + " scenes"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
                }
                StatusBadge { text: (root.controller.plan.status || "review").replace(/_/g," "); status: root.controller.plan.status === "applied" ? "ready" : (root.controller.plan.status === "outdated" ? "warning" : "info") }
            }
            InfoBanner { Layout.fillWidth: true; visible: root.controller.plan.metadata && root.controller.plan.metadata.offline; text: "Local Director • Offline planning • No project text leaves this device."; variant: "info" }
            Repeater {
                model: root.controller.plan.metadata && root.controller.plan.metadata.notices ? root.controller.plan.metadata.notices : []
                delegate: InfoBanner { required property var modelData; Layout.fillWidth: true; text: modelData; variant: "warning" }
            }
            AppCard {
                Layout.fillWidth: true
                visible: root.controller.comparison && Object.keys(root.controller.comparison).length > 0
                implicitHeight: comparisonColumn.implicitHeight + Theme.spacing.lg * 2
                ColumnLayout {
                    id: comparisonColumn
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.lg
                    spacing: Theme.spacing.xs
                    Text { text: "What changed"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                    Repeater {
                        model: root.controller.comparison ? Object.keys(root.controller.comparison) : []
                        delegate: Text {
                            required property string modelData
                            Layout.fillWidth: true
                            text: modelData + ": " + JSON.stringify(root.controller.comparison[modelData].previous) + " → " + JSON.stringify(root.controller.comparison[modelData].new)
                            color: Theme.colors.textSecondary
                            font.family: Theme.type.family
                            font.pixelSize: Theme.type.bodySmall
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
            Text { text: "Recommendations"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
            GridLayout {
                Layout.fillWidth: true; columns: width < 860 ? 1 : 2; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.md
                Repeater { model: root.controller.plan.recommendations || []; delegate: DirectorRecommendationCard { required property var modelData; Layout.fillWidth: true; recommendation: modelData; controller: root.controller } }
            }
            RowLayout { Layout.fillWidth: true
                Text { text: "Scene Plan"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                Item { Layout.fillWidth: true }
                SecondaryButton { text: "Regenerate Scenes"; compact: true; onClicked: root.controller.regenerate("scenes") }
            }
            Repeater { model: root.controller.scenePlans; delegate: DirectorScenePlan { required property var modelData; Layout.fillWidth: true; scene: modelData; controller: root.controller } }
            RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.sm
                SecondaryButton { text: "Regenerate Unlocked"; onClicked: root.controller.regenerate("all_unlocked") }
                SecondaryButton { text: "Approve"; onClicked: root.controller.approve() }
                Item { Layout.fillWidth: true }
                AppButton { text: "Apply Plan"; onClicked: root.applyRequested() }
            }
            Item { Layout.preferredHeight: Theme.spacing.xl }
        }
    }
}
