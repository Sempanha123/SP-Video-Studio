import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Rectangle {
    id: root
    property var beat
    property var controller
    width: parent ? parent.width : 600; height: 126; radius: Theme.radius.medium; color: Theme.colors.surface2; border.color: beat.locked ? Theme.colors.warning : Theme.colors.border
    function openEditor() {
        titleField.text=beat.title||""; descriptionField.text=beat.description||""; durationField.text=String(beat.targetDurationMs||5000)
        visualField.text=beat.visualDirection||""; characterField.text=beat.characterId||""; notesField.text=beat.notes||""; lockCheck.checked=!!beat.locked
        var types=["hook","setup","context","character","development","conflict","discovery","turning_point","climax","resolution","lesson","outro","problem","struggle","explanation","example","current_state","closing","custom"]
        typeBox.currentIndex=Math.max(0,types.indexOf(beat.type||"custom"))
        var emotions=["neutral","warm","tense","hopeful","sad","excited","calm"]; emotionBox.currentIndex=Math.max(0,emotions.indexOf(beat.emotion||"neutral")); editDialog.open()
    }
    RowLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: Theme.spacing.md
        Rectangle { Layout.preferredWidth: 34; Layout.preferredHeight: 34; radius: 17; color: Theme.colors.accentSoft; Text { anchors.centerIn: parent; text: String((beat.order||0)+1).padStart(2,"0"); color: Theme.colors.accent; font.weight: Theme.type.semibold } }
        ColumnLayout { Layout.fillWidth: true; spacing: 2
            Text { text: (beat.type||"custom").replace(/_/g," ").toUpperCase()+"  •  "+Math.round((beat.targetDurationMs||0)/1000)+" sec"; color: Theme.colors.textMuted; font.pixelSize: Theme.type.caption }
            Text { text: beat.title||"Untitled beat"; color: Theme.colors.textPrimary; font.weight: Theme.type.semibold; font.pixelSize: Theme.type.bodyLarge; elide: Text.ElideRight; Layout.fillWidth: true }
            Text { text: beat.description||"Add the narrative purpose for this beat."; color: Theme.colors.textSecondary; elide: Text.ElideRight; Layout.fillWidth: true }
            Text { visible: (beat.visualDirection||"")!==""; text: "Visual: "+beat.visualDirection; color: Theme.colors.textMuted; elide: Text.ElideRight; Layout.fillWidth: true; font.pixelSize: Theme.type.caption }
        }
        SecondaryButton { text:"Edit"; compact:true; onClicked:root.openEditor() }
        SecondaryButton { text: beat.locked ? "Locked" : "Lock"; compact: true; onClicked: if (root.controller) root.controller.updateBeat(beat.id,beat.title,beat.description,beat.targetDurationMs,beat.type,beat.visualDirection,!beat.locked) }
        SecondaryButton { text: "↑"; compact: true; onClicked: if(root.controller) root.controller.moveBeat(beat.id,-1) }
        SecondaryButton { text: "↓"; compact: true; onClicked: if(root.controller) root.controller.moveBeat(beat.id,1) }
        SecondaryButton { text: "Copy"; compact: true; onClicked: if(root.controller) root.controller.duplicateBeat(beat.id) }
        IconButton { iconName: "trash"; tooltip: "Delete beat only; linked production items remain"; onClicked: if(root.controller) root.controller.deleteBeat(beat.id) }
    }
    Dialog {
        id:editDialog; modal:true; anchors.centerIn:Overlay.overlay; width:Math.min(680,root.Window.width-48); title:"Edit Story Beat"; standardButtons:Dialog.NoButton
        ColumnLayout { width:parent.width; spacing:Theme.spacing.sm
            AppTextField { id:titleField; Layout.fillWidth:true; placeholderText:"Beat title" }
            TextArea { id:descriptionField; Layout.fillWidth:true; Layout.preferredHeight:90; placeholderText:"Narrative purpose / description"; wrapMode:TextEdit.Wrap; color:Theme.colors.textPrimary; background:Rectangle { radius:Theme.radius.medium; color:Theme.colors.surface2; border.color:Theme.colors.border } }
            RowLayout { Layout.fillWidth:true
                AppComboBox { id:typeBox; Layout.fillWidth:true; model:["hook","setup","context","character","development","conflict","discovery","turning_point","climax","resolution","lesson","outro","problem","struggle","explanation","example","current_state","closing","custom"] }
                AppComboBox { id:emotionBox; Layout.fillWidth:true; model:["neutral","warm","tense","hopeful","sad","excited","calm"] }
                AppTextField { id:durationField; Layout.preferredWidth:130; placeholderText:"Duration ms" }
            }
            AppTextField { id:visualField; Layout.fillWidth:true; placeholderText:"Visual direction, e.g. Wide city shot at night" }
            AppTextField { id:characterField; Layout.fillWidth:true; placeholderText:"Character ID (optional)" }
            AppTextField { id:notesField; Layout.fillWidth:true; placeholderText:"Production notes (optional)" }
            CheckBox { id:lockCheck; text:"Lock this beat during structure refresh" }
            RowLayout { Layout.fillWidth:true; Item { Layout.fillWidth:true }; SecondaryButton { text:"Cancel"; onClicked:editDialog.close() }; AppButton { text:"Save Beat"; onClicked:{ if(root.controller) root.controller.editBeat(beat.id,titleField.text,descriptionField.text,Math.max(1,Number(durationField.text)),typeBox.currentText,emotionBox.currentText,visualField.text,characterField.text,notesField.text,lockCheck.checked); editDialog.close() } } }
        }
    }
}
