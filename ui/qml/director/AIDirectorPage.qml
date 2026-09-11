import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property string projectLanguage: "en"
    signal toastRequested(string message, string variant)

    SplitView {
        anchors.fill: parent; orientation: root.width < 1120 ? Qt.Vertical : Qt.Horizontal
        AppCard {
            SplitView.preferredWidth: 320; SplitView.minimumWidth: 280; SplitView.fillHeight: true
            ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
                RowLayout { Layout.fillWidth: true
                    ColumnLayout { Layout.fillWidth: true; spacing: 1
                        Text { text: "AI Director"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
                        Text { text: "Local production planning"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    }
                    AppButton { text: "+ Plan"; compact: true; onClicked: setup.visible = true }
                }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: Theme.spacing.sm; model: root.controller ? root.controller.plans : []
                    delegate: AppCard {
                        required property var modelData; width: ListView.view.width; implicitHeight: 110
                        selected: root.controller && root.controller.plan.id === modelData.id
                        interactive: true
                        onClicked: root.controller.selectPlan(modelData.id)
                        ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: 3
                            RowLayout { Layout.fillWidth: true
                                Text { Layout.fillWidth: true; text: modelData.platform.replace(/_/g," "); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideRight }
                                StatusBadge { visible: modelData.active; text: "Active"; status: "ready" }
                            }
                            Text { text: (modelData.targetDurationMs/1000).toFixed(0) + " sec • " + modelData.aspectRatio + " • " + modelData.sceneCount + " scenes"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                            Text { text: modelData.status.replace(/_/g," "); color: modelData.status === "outdated" ? Theme.colors.warning : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        }
                    }
                }
                RowLayout { Layout.fillWidth: true; visible: root.controller && !!root.controller.plan.id
                    SecondaryButton { text: "Duplicate"; compact: true; onClicked: root.controller.duplicatePlan() }
                    Item { Layout.fillWidth: true }
                    AppButton { text: "Delete"; compact: true; variant: "danger"; onClicked: deleteDialog.open() }
                }
            }
        }
        Item {
            SplitView.fillWidth: true; SplitView.fillHeight: true; SplitView.minimumWidth: 540
            DirectorSetup { id: setup; anchors.fill: parent; visible: !root.controller || !root.controller.plan.id; controller: root.controller; projectLanguage: root.projectLanguage; onCreated: visible=false }
            DirectorPlanReview { anchors.fill: parent; visible: root.controller && !!root.controller.plan.id; controller: root.controller; onApplyRequested: applyDialog.open() }
        }
    }
    DirectorApplyDialog { id: applyDialog; controller: root.controller }
    Dialog { id: deleteDialog; modal: true; title: "Delete Director Plan?"; standardButtons: Dialog.Yes | Dialog.No; contentItem: Text { text: "Deleting a plan does not remove scenes, scripts, media, voices, or subtitles that were previously applied."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family }; onAccepted: root.controller.deletePlan() }
    Connections { target: root.controller; ignoreUnknownSignals: true; function onOperationSucceeded(message){root.toastRequested(message,"success")} function onOperationFailed(message){root.toastRequested(message,"error")} }
}
