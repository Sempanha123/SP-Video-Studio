import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import SPVideoStudio.Phase27 1.0
Dialog {
    id: root; modal: true; width: Math.min(760, parent ? parent.width - 48 : 760); height: Math.min(620, parent ? parent.height - 48 : 620); closePolicy: Popup.NoAutoClose
    property var reviewData: ({})
    Component.onCompleted: { Recovery.refreshRecoveries(); if (Recovery.hasRecoverableWork) open() }
    Connections { target: Recovery; function onRecoveryChanged() { if (Recovery.hasRecoverableWork && !root.visible) root.open() } }
    contentItem: ColumnLayout { spacing: 12
        Text { text: "MMO Video Studio found recoverable work."; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading; font.weight: Theme.type.semibold }
        Text { text: "A newer unsaved version was found. Saved projects are never overwritten automatically."; color: Theme.colors.textSecondary; font.family: Theme.type.family; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true
            ColumnLayout { width: parent.width; spacing: 10
                Repeater { model: Recovery.recoveries
                    delegate: RecoveryCard { snapshot: modelData
                        onRecoverRequested: function(id) { if (Recovery.recoverSnapshot(id) && !Recovery.hasRecoverableWork) root.close() }
                        onSavedRequested: function(id) { Recovery.openSavedVersion(id); root.close() }
                        onReviewRequested: function(id) { root.reviewData = Recovery.review(id); reviewBox.visible = true }
                        onDiscardRequested: function(id) { Recovery.discardSnapshot(id); if (!Recovery.hasRecoverableWork) root.close() }
                    }
                }
            }
        }
        Rectangle { id: reviewBox; visible: false; Layout.fillWidth: true; implicitHeight: review.implicitHeight + 24; radius: 10; color: Theme.colors.surface; border.color: Theme.colors.border
            RecoveryComparison { id: review; anchors.fill: parent; anchors.margins: 12; comparison: root.reviewData.comparison || ({}) }
        }
        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true }; Button { text: "Later"; onClicked: root.close() } }
    }
}
