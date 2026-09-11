import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

ScrollView {
    id: root
    property var controller
    property var scene: controller ? controller.scene : ({})
    property bool compact: false
    signal chooseMediaRequested()
    signal chooseLogoRequested()
    clip: true

    ColumnLayout {
        width: Math.max(300, root.availableWidth - 10)
        spacing: Theme.spacing.md

        AppCard {
            Layout.fillWidth: true; implicitHeight: generalCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout {
                id: generalCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "General"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                    Item { Layout.fillWidth: true }
                    AppSwitch { checked: root.scene.enabled !== false; onToggled: if (root.controller) root.controller.setEnabled(checked) }
                }
                TextField { id: nameField; Layout.fillWidth: true; text: root.scene.name || ""; placeholderText: "Scene name" }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Duration"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    SpinBox { id: durationBox; Layout.fillWidth: true; from: 100; to: 3600000; stepSize: 100; value: root.scene.durationMs || 5000; editable: true }
                    Text { text: "ms"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                }
                SecondaryButton { text: "Save General"; compact: true; onClicked: if (root.controller) root.controller.updateGeneral(nameField.text, durationBox.value) }
                RowLayout {
                    visible: (root.scene.scriptSectionId || "") !== ""
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: root.scene.sourceStatus === "source_changed" ? "Source script changed" : (root.scene.sourceStatus === "source_missing" ? "Source script missing" : "Linked to script section"); color: root.scene.sourceStatus === "current" ? Theme.colors.textMuted : Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SecondaryButton { text: "Sync"; compact: true; enabled: root.scene.sourceStatus !== "source_missing"; onClicked: if (root.controller) root.controller.syncCurrentFromScript() }
                }
            }
        }

        AppCard {
            Layout.fillWidth: true; implicitHeight: visualCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout {
                id: visualCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                Text { text: "Visual"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                Text { Layout.fillWidth: true; text: root.scene.mediaName || "No media selected"; elide: Text.ElideRight; color: root.scene.mediaName ? Theme.colors.textPrimary : Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                RowLayout {
                    Layout.fillWidth: true
                    AppButton { text: root.scene.primaryMediaId ? "Replace Media" : "Choose Media"; compact: true; onClicked: root.chooseMediaRequested() }
                    SecondaryButton { visible: !!root.scene.primaryMediaId; text: "Clear"; compact: true; onClicked: if (root.controller) root.controller.clearMedia() }
                }
                ComboBox {
                    Layout.fillWidth: true; visible: !!root.scene.primaryMediaId
                    model: ["Fill", "Fit", "Stretch"]
                    currentIndex: Math.max(0,["fill","fit","stretch"].indexOf(root.scene.fitMode || "fill"))
                    onActivated: if (root.controller) root.controller.setFitMode(["fill","fit","stretch"][currentIndex])
                }
                GridLayout {
                    visible: root.scene.mediaType === "video"; Layout.fillWidth: true; columns: 2
                    Text { text: "Start ms"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: videoStart; Layout.fillWidth: true; from: 0; to: Math.max(0, root.scene.mediaDurationMs || 3600000); value: root.scene.sourceStartMs || 0; editable: true }
                    Text { text: "End ms"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SpinBox { id: videoEnd; Layout.fillWidth: true; from: 1; to: Math.max(1, root.scene.mediaDurationMs || 3600000); value: root.scene.sourceEndMs > 0 ? root.scene.sourceEndMs : Math.max(1,root.scene.mediaDurationMs || root.scene.durationMs || 5000); editable: true }
                    SecondaryButton { text: "Apply Range"; compact: true; onClicked: if (root.controller) root.controller.setVideoRange(videoStart.value,videoEnd.value) }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Use background"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
                    Item { Layout.fillWidth: true }
                    AppSwitch { checked: root.scene.backgroundEnabled || false; onToggled: if (root.controller) root.controller.setBackgroundEnabled(checked) }
                }
                TextField { Layout.fillWidth: true; visible: root.scene.backgroundEnabled || false; text: root.scene.backgroundColor || "#10131A"; placeholderText: "#10131A"; onEditingFinished: if (root.controller) root.controller.setBackground(text) }
            }
        }

        AppCard {
            Layout.fillWidth: true; implicitHeight: audioCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout {
                id: audioCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                Text { text: "Audio"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                ComboBox {
                    id: narrationBox; Layout.fillWidth: true
                    model: [{id:"",name:"No narration"}].concat(root.controller ? root.controller.narrationOptions : [])
                    textRole: "name"
                    Component.onCompleted: syncNarration()
                    function syncNarration() { var wanted=root.scene.narrationAudioId || ""; for(var i=0;i<model.length;i++) if(model[i].id===wanted){ currentIndex=i; return } currentIndex=0 }
                    onActivated: if (root.controller) root.controller.assignNarration(model[currentIndex].id)
                }
                RowLayout {
                    visible: (root.scene.narrationAudioId || "") !== ""; Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: root.scene.narrationName || "Narration"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                    SecondaryButton { text: "Play"; compact: true; onClicked: if (root.controller) root.controller.playNarration() }
                    SecondaryButton { visible: (root.scene.narrationDurationMs || 0) > (root.scene.durationMs || 0); text: "Match Duration"; compact: true; onClicked: if (root.controller) root.controller.matchNarrationDuration() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    CheckBox { id: sourceAudio; text: "Source audio"; checked: root.scene.audio ? root.scene.audio.sourceAudioEnabled : false }
                    SpinBox { id: sourceVol; from: 0; to: 100; value: Math.round((root.scene.audio ? root.scene.audio.sourceAudioVolume : 1)*100); editable: true; Layout.fillWidth: true }
                }
                RowLayout {
                    Layout.fillWidth: true
                    CheckBox { id: narrationAudio; text: "Narration"; checked: root.scene.audio ? root.scene.audio.narrationEnabled : true }
                    SpinBox { id: narrationVol; from: 0; to: 100; value: Math.round((root.scene.audio ? root.scene.audio.narrationVolume : 1)*100); editable: true; Layout.fillWidth: true }
                }
                SecondaryButton { text: "Apply Audio"; compact: true; onClicked: if (root.controller) root.controller.setAudio(sourceAudio.checked,sourceVol.value,narrationAudio.checked,narrationVol.value) }
            }
        }

        AppCard {
            Layout.fillWidth: true; implicitHeight: subsCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout {
                id: subsCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                Text { text: "Subtitles"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                ComboBox {
                    Layout.fillWidth: true
                    model: [{id:"",name:"No subtitle track"}].concat(root.controller ? root.controller.subtitleOptions : [])
                    textRole: "name"
                    onActivated: if (root.controller) root.controller.assignSubtitle(model[currentIndex].id)
                }
                Text { visible: !!root.scene.subtitleName; text: "Selected: " + (root.scene.subtitleName || ""); color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            }
        }

        AppCard {
            Layout.fillWidth: true; implicitHeight: overlayCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout {
                id: overlayCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.sm
                SceneOverlayEditor { Layout.fillWidth: true; controller: root.controller; overlays: root.controller ? root.controller.overlays : []; onAddLogoRequested: root.chooseLogoRequested() }
            }
        }

        AppCard {
            Layout.fillWidth: true; implicitHeight: transitionCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout { id: transitionCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; SceneTransitionPicker { Layout.fillWidth: true; controller: root.controller; scene: root.scene } }
        }

        AppCard {
            visible: root.controller && root.controller.issues.length > 0
            Layout.fillWidth: true; implicitHeight: issueCol.implicitHeight + Theme.spacing.lg*2
            ColumnLayout {
                id: issueCol; anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.xs
                Text { text: "Scene Validation"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold }
                Repeater { model: root.controller ? root.controller.issues : []; delegate: Text { Layout.fillWidth: true; text: "• " + (modelData.message || "Scene warning"); wrapMode: Text.WordWrap; color: modelData.severity === "error" ? Theme.colors.danger : Theme.colors.warning; font.family: Theme.type.family; font.pixelSize: Theme.type.caption } }
            }
        }
    }
}
