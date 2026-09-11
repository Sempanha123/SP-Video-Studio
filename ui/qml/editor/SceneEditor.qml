import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property var playbackController
    property string aspectRatio: "16:9"
    signal toastRequested(string message, string variant)

    SplitView {
        anchors.fill: parent
        orientation: root.width < 1180 ? Qt.Vertical : Qt.Horizontal

        AppCard {
            SplitView.preferredWidth: Math.min(390, root.width * .30)
            SplitView.minimumWidth: 320
            SplitView.fillHeight: true
            SceneList {
                anchors.fill: parent
                anchors.margins: Theme.spacing.lg
                controller: root.controller
                onCreateFromTranscriptRequested: transcriptDialog.open()
            }
        }

        ColumnLayout {
            SplitView.fillWidth: true
            SplitView.fillHeight: true
            SplitView.minimumWidth: 460
            spacing: Theme.spacing.md

            ScenePreview {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 320
                controller: root.controller
                playbackController: root.playbackController
                aspectRatio: root.aspectRatio
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spacing.sm
                SecondaryButton { text: "Move Up"; compact: true; enabled: !!root.controller && !!root.controller.scene.id; onClicked: root.controller.moveScene(-1) }
                SecondaryButton { text: "Move Down"; compact: true; enabled: !!root.controller && !!root.controller.scene.id; onClicked: root.controller.moveScene(1) }
                SecondaryButton { text: "Duplicate"; compact: true; enabled: !!root.controller && !!root.controller.scene.id; onClicked: root.controller.duplicateScene() }
                Item { Layout.fillWidth: true }
                AppButton { text: "Delete Scene"; variant: "danger"; compact: true; enabled: !!root.controller && !!root.controller.scene.id; onClicked: deleteDialog.open() }
            }
        }

        SceneInspector {
            SplitView.preferredWidth: 360
            SplitView.minimumWidth: 320
            SplitView.fillHeight: true
            controller: root.controller
            onChooseMediaRequested: { mediaPicker.logoOnly=false; mediaPicker.open() }
            onChooseLogoRequested: { mediaPicker.logoOnly=true; mediaPicker.open() }
        }
    }

    SceneMediaPicker {
        id: mediaPicker
        controller: root.controller
        onMediaChosen: function(mediaId) {
            if (!root.controller) return
            if (logoOnly) root.controller.addLogo(mediaId)
            else root.controller.assignMedia(mediaId)
        }
    }

    Dialog {
        id: transcriptDialog
        modal: true
        width: 440
        title: "Create Scenes from Transcript"
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: ColumnLayout {
            spacing: Theme.spacing.md
            Text { Layout.fillWidth: true; text: "Group transcript segments into storyboard scenes instead of creating one scene for every tiny segment."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            ComboBox { id: transcriptBox; Layout.fillWidth: true; model: root.controller ? root.controller.transcriptOptions : []; textRole: "name" }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Approx. group length"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                SpinBox { id: groupSeconds; from: 5; to: 60; value: 15; editable: true; Layout.fillWidth: true }
                Text { text: "sec"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
        }
        onAccepted: if (root.controller && transcriptBox.currentIndex >= 0) root.controller.createFromTranscript(transcriptBox.model[transcriptBox.currentIndex].id, groupSeconds.value)
    }

    Dialog {
        id: deleteDialog
        modal: true
        width: 420
        title: "Delete Scene?"
        standardButtons: Dialog.Yes | Dialog.No
        contentItem: Text { text: "This removes only the scene and its scene-owned overlays. Project media, narration, and subtitle tracks are kept."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
        onAccepted: if (root.controller) root.controller.deleteScene()
    }

    Connections {
        target: root.controller
        ignoreUnknownSignals: true
        function onOperationSucceeded(message) { root.toastRequested(message, "success") }
        function onOperationFailed(message) { root.toastRequested(message, "error") }
    }
}
