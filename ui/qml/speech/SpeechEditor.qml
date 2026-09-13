import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.ManualSpeech 1.0
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

FocusScope {
    id: root
    property var controller: ManualSpeech
    property string editingId: ""
    property string projectId: ""
    property string scriptSectionId: ""
    signal toastRequested(string message, string variant)

    function rowSelected(id) { return controller && controller.selectedIds.indexOf(id) >= 0 }
    function claimContext(){ if(root.activeFocus) Commands.setContext("speech_editor") }
    function handleSpeechCommand(commandId){
        if(!controller) return false
        if(commandId==="speech.generate") { controller.generateSelected(); return true }
        if(commandId==="speech.find") { findField.forceActiveFocus(); return true }
        if(commandId==="speech.delete") { if(root.editingId==="") controller.deleteSelected(); return true }
        if(commandId==="speech.duplicate") { controller.duplicateSelected(); return true }
        if(commandId==="speech.select_all") { controller.selectAll(); return true }
        if(commandId==="speech.previous") { controller.selectRelative(-1); table.forceActiveFocus(); return true }
        if(commandId==="speech.next") { controller.selectRelative(1); table.forceActiveFocus(); return true }
        if(commandId==="speech.edit") {
            var row=controller.selectedRow
            if(row && row.id) { root.editingId=String(row.id); table.forceActiveFocus(); return true }
            return false
        }
        if(commandId==="speech.generate_outdated") { controller.generateOutdated(); return true }
        if(commandId==="app.escape") {
            if(root.editingId!=="") { root.editingId=""; table.forceActiveFocus(); return true }
            controller.clearSelection(); return true
        }
        if(commandId==="playback.toggle") { controller.togglePreview(); return true }
        return false
    }

    Component.onCompleted: { if(controller && projectId) controller.setCurrentProject(projectId); Commands.setProjectOpen(projectId.length>0) }
    onProjectIdChanged: { if(controller) controller.setCurrentProject(projectId); Commands.setProjectOpen(projectId.length>0) }
    onActiveFocusChanged: claimContext()
    onEditingIdChanged: Commands.setTextEditing(root.editingId !== "")

    ColumnLayout {
        anchors.fill: parent; spacing: Theme.spacing.sm
        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
            AppButton { text: "+ Add Speech"; compact: true; onClicked: controller.addSpeech(root.scriptSectionId, "New speech") }
            SecondaryButton { text: "Split"; compact: true; enabled: controller.selectedCount === 1; ToolTip.text: "Split speech"; onClicked: splitDialog.open() }
            SecondaryButton { text: "Merge"; compact: true; enabled: controller.selectedCount === 2; onClicked: mergeDialog.open() }
            SecondaryButton { text: "Delete"; compact: true; enabled: controller.selectedCount > 0; ToolTip.text: "Delete · " + Commands.shortcutFor("speech.delete"); onClicked: controller.deleteSelected() }
            AppTextField { id: findField; Layout.preferredWidth: 160; placeholderText: "Find"; onActiveFocusChanged: Commands.setTextEditing(activeFocus) }
            AppTextField { id: replaceField; Layout.preferredWidth: 150; placeholderText: "Replace"; onActiveFocusChanged: Commands.setTextEditing(activeFocus) }
            SecondaryButton { text: "Replace Selected"; compact: true; onClicked: controller.replaceText(findField.text, replaceField.text, "selected") }
            Item { Layout.fillWidth: true }
            SecondaryButton { text: "Select Outdated"; compact: true; onClicked: controller.selectStatus("outdated") }
            SecondaryButton { text: "Generate Selected"; compact: true; enabled: controller.selectedCount > 0 && !controller.busy; ToolTip.text: "Generate Speech · " + Commands.shortcutFor("speech.generate"); onClicked: controller.generateSelected() }
            SecondaryButton { text: "Generate Outdated"; compact: true; enabled: !controller.busy; onClicked: controller.generateOutdated() }
            AppButton { text: "Generate All"; compact: true; enabled: !controller.busy; onClicked: controller.generateAll() }
        }

        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
            SecondaryButton { text: "Select All"; compact: true; ToolTip.text: "Select all · " + Commands.shortcutFor("speech.select_all"); onClicked: controller.selectAll() }
            SecondaryButton { text: "Duplicate"; compact: true; enabled: controller.selectedCount===1; ToolTip.text: "Duplicate · " + Commands.shortcutFor("speech.duplicate"); onClicked: controller.duplicateSelected() }
            SecondaryButton { text: "Select Failed"; compact: true; onClicked: controller.selectStatus("failed") }
            SecondaryButton { text: "Select Ungenerated"; compact: true; onClicked: controller.selectStatus("ungenerated") }
            Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 24; color: Theme.colors.border }
            AppComboBox { id: speakerPicker; Layout.preferredWidth: 150; model: controller.speakers; textRole: "name" }
            SecondaryButton { text: "Set Speaker"; compact: true; enabled: controller.selectedCount>0 && speakerPicker.currentIndex>=0; onClicked: { var x=controller.speakers[speakerPicker.currentIndex]; if(x)controller.setSpeakerSelected(x.id) } }
            AppComboBox { id: voicePicker; Layout.preferredWidth: 175; model: controller.voices; textRole: "name" }
            IconButton { iconName: "play"; tooltip: "Preview selected voice"; enabled: voicePicker.currentIndex>=0; onClicked: { var x=controller.voices[voicePicker.currentIndex]; if(x)controller.previewVoice(x.id) } }
            SecondaryButton { text: "Set Voice"; compact: true; enabled: controller.selectedCount>0 && voicePicker.currentIndex>=0; onClicked: { var x=controller.voices[voicePicker.currentIndex]; if(x)controller.setVoiceSelected(x.id) } }
            AppComboBox { id: languagePicker; Layout.preferredWidth: 92; model: ["en","km","th","vi"] }
            SecondaryButton { text: "Set Language"; compact: true; enabled: controller.selectedCount>0; onClicked: controller.setLanguageSelected(String(languagePicker.currentText)) }
            Item { Layout.fillWidth: true }
        }

        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
            Text { text: "Voice filters"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppComboBox { id: voiceLanguageFilter; Layout.preferredWidth: 92; model: ["all","en","km","th","vi"]; onActivated: controller.filterVoices(currentText, voiceRoleFilter.currentText, styleFilter.text, toneFilter.text, energyFilter.text, favoritesFilter.checked) }
            AppComboBox { id: voiceRoleFilter; Layout.preferredWidth: 130; model: ["all","reporter","narrator","interview","character","professional"]; onActivated: controller.filterVoices(voiceLanguageFilter.currentText, currentText, styleFilter.text, toneFilter.text, energyFilter.text, favoritesFilter.checked) }
            AppTextField { id: styleFilter; Layout.preferredWidth: 110; placeholderText: "Style"; onEditingFinished: controller.filterVoices(voiceLanguageFilter.currentText, voiceRoleFilter.currentText, text, toneFilter.text, energyFilter.text, favoritesFilter.checked); onActiveFocusChanged: Commands.setTextEditing(activeFocus) }
            AppTextField { id: toneFilter; Layout.preferredWidth: 100; placeholderText: "Tone"; onEditingFinished: controller.filterVoices(voiceLanguageFilter.currentText, voiceRoleFilter.currentText, styleFilter.text, text, energyFilter.text, favoritesFilter.checked); onActiveFocusChanged: Commands.setTextEditing(activeFocus) }
            AppTextField { id: energyFilter; Layout.preferredWidth: 100; placeholderText: "Energy"; onEditingFinished: controller.filterVoices(voiceLanguageFilter.currentText, voiceRoleFilter.currentText, styleFilter.text, toneFilter.text, text, favoritesFilter.checked); onActiveFocusChanged: Commands.setTextEditing(activeFocus) }
            CheckBox { id: favoritesFilter; text: "Favorites"; onToggled: controller.filterVoices(voiceLanguageFilter.currentText, voiceRoleFilter.currentText, styleFilter.text, toneFilter.text, energyFilter.text, checked) }
            Item { Layout.fillWidth: true }
        }

        RowLayout { Layout.fillWidth: true; visible: controller.busy; spacing: Theme.spacing.sm
            ProgressBar { Layout.fillWidth: true; from: 0; to: Math.max(1, controller.generationTotal); value: controller.generationCurrent }
            Text { text: "Generating " + controller.generationCurrent + " / " + controller.generationTotal + " · " + controller.generationLabel; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            SecondaryButton { text: "Cancel Remaining"; compact: true; onClicked: controller.cancelGeneration() }
        }

        RowLayout { Layout.fillWidth: true; spacing: 0
            Repeater { model: ["Select","Start","End","Speaker","Lang","Text","Voice Profile","Duration Status","Audio Status","Actions"]; delegate: Rectangle { required property string modelData; height: 30; width: modelData === "Text" ? 310 : (modelData === "Select" ? 46 : 104); color: Theme.colors.surfaceRaised; border.color: Theme.colors.border
                Text { anchors.centerIn: parent; text: modelData; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption; font.weight: Theme.type.semibold }
            } }
        }

        SplitView { Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Horizontal
            ListView {
                id: table
                focus: true
                SplitView.fillWidth: true; SplitView.minimumWidth: 780; clip: true; model: controller.rows; spacing: 1; reuseItems: true; cacheBuffer: 160
                onActiveFocusChanged: if(activeFocus && root.editingId==="") { Commands.setTextEditing(false); Commands.setContext("speech_editor") }
                delegate: SpeechRow {
                    required property var modelData
                    width: table.width; rowData: modelData; selected: root.rowSelected(modelData.id); editing: root.editingId === modelData.id
                    onSelectRequested: function(value){ controller.select(modelData.id, value); table.forceActiveFocus(); Commands.setContext("speech_editor") }
                    onEditRequested: { root.editingId = modelData.id; Commands.setTextEditing(true) }
                    onTextCommitted: function(value){ root.editingId = ""; Commands.setTextEditing(false); controller.editText(modelData.id, value); table.forceActiveFocus() }
                    onTimingCommitted: function(startText,endText){ controller.setTimingText(modelData.id,startText,endText) }
                    onPlayRequested: if(modelData.activeGeneratedAudioId) controller.playTake(modelData.activeGeneratedAudioId)
                    onRegenerateRequested: { controller.clearSelection(); controller.select(modelData.id,true); controller.generateSelected() }
                    MouseArea { anchors.fill: parent; acceptedButtons: Qt.NoButton; onWheel: function(wheel){ wheel.accepted=false } }
                }
            }
            SpeechInspector { SplitView.preferredWidth: 310; SplitView.minimumWidth: 270; controller: root.controller }
        }
    }

    AppDialog { id: splitDialog; width: 480; parent: Overlay.overlay; header: null; footer: null
        onOpened: Commands.setModalOpen(true)
        onClosed: Commands.setModalOpen(false)
        contentItem: ColumnLayout { spacing: Theme.spacing.sm
            Text { text: "Split Speech"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading }
            AppTextField { id: splitBefore; Layout.fillWidth: true; placeholderText: "Text before split" }
            AppTextField { id: splitAfter; Layout.fillWidth: true; placeholderText: "Text after split" }
            AppTextField { id: splitTime; Layout.fillWidth: true; placeholderText: "Split time in milliseconds" }
            RowLayout { Item { Layout.fillWidth: true } SecondaryButton { text: "Cancel"; onClicked: splitDialog.close() } AppButton { text: "Split"; onClicked: { var r=controller.selectedRow; if(controller.splitBlock(r.id,splitBefore.text,splitAfter.text,Number(splitTime.text))) splitDialog.close() } } }
        }
    }
    AppDialog { id: mergeDialog; width: 420; parent: Overlay.overlay; header: null; footer: null
        onOpened: Commands.setModalOpen(true)
        onClosed: Commands.setModalOpen(false)
        contentItem: ColumnLayout { spacing: Theme.spacing.sm
            Text { text: "Merge adjacent speech"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.heading }
            Text { text: "Compatible speaker/voice settings are preserved. If they differ, assign the desired speaker/voice first."; wrapMode: Text.WordWrap; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            RowLayout { Item { Layout.fillWidth: true } SecondaryButton { text: "Cancel"; onClicked: mergeDialog.close() } AppButton { text: "Merge"; onClicked: { var ids=controller.selectedIds; if(ids.length===2 && controller.mergeBlocks(ids[0],ids[1],"","")) mergeDialog.close() } } }
        }
    }
    Connections { target: Commands; function onCommandTriggered(commandId){ if(Commands.context==="speech_editor" || commandId==="playback.toggle") root.handleSpeechCommand(commandId) } }
    Connections { target: controller; function onOperationSucceeded(message){ root.toastRequested(message,"success") } function onOperationFailed(message){ root.toastRequested(message,"error") } }
}
