import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

Dialog {
    id: root
    property var controller
    modal: true; width: 520; title: "Apply Production Plan"
    standardButtons: Dialog.Ok | Dialog.Cancel
    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        Text { Layout.fillWidth: true; text: "Choose how this plan should affect the project. Existing scenes are never replaced unless you explicitly select that option."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        AppComboBox { id: mode; Layout.fillWidth: true; model: ["Apply Settings Only","Add Planned Scenes","Replace Existing Scenes"] }
        InfoBanner { Layout.fillWidth: true; visible: root.controller && root.controller.applyImpact.hasSceneConflict && mode.currentIndex===2; text: "This project already has scenes. Replace Existing Scenes deletes scene records only after this explicit confirmation; shared media and generated audio remain."; variant: "warning" }
        Text { text: "Voice (optional)"; color: Theme.colors.textSecondary; font.family: Theme.type.family }
        AppComboBox { id: voice; Layout.fillWidth: true; model: [{id:"",name:"Keep Current Voice"}].concat(root.controller ? root.controller.voiceMatches : []); textRole: "name" }
        Text { Layout.fillWidth: true; text: root.controller ? ("Aspect ratio → " + root.controller.applyImpact.aspectRatio + " • Planned scenes: " + root.controller.applyImpact.plannedScenes) : ""; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
    }
    onAccepted: {
        var modes=["settings_only","add_scenes","replace_scenes"]
        var voiceId=voice.currentIndex>=0 ? voice.model[voice.currentIndex].id : ""
        root.controller.apply(modes[mode.currentIndex],voiceId)
    }
}
