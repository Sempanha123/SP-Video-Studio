import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "../theme"
import "../components"

Item {
    id: root
    property var controller
    property string selectedPresetId: ""
    property int exportWidth: 1920
    property int exportHeight: 1080
    property int exportFps: 30
    property string quality: "balanced"
    property string encoder: "auto"
    property string subtitleMode: "none"
    property string subtitleTrackId: ""
    property string outputFolder: ""
    property string filename: "video.mp4"
    property string overwritePolicy: "keep_both"
    property string fitMode: "fill"
    property bool audioEnabled: true
    property string audioQuality: "high"
    property bool keepTemp: false
    property bool rememberProject: true

    function loadDraft() {
        if (!controller || !controller.draft) return
        var d=controller.draft
        selectedPresetId=d.presetId || ""
        exportWidth=Number(d.width || 1920); exportHeight=Number(d.height || 1080); exportFps=Number(d.fps || 30)
        quality=d.quality || "balanced"; encoder=d.encoder || "auto"; subtitleMode=d.subtitleMode || "none"; subtitleTrackId=d.subtitleTrackId || ""
        outputFolder=d.outputFolder || ""; filename=d.filename || "video.mp4"; overwritePolicy=d.overwritePolicy || "keep_both"; fitMode=d.fitMode || "fill"
        audioEnabled=d.audioEnabled !== false; audioQuality=d.audioQuality || "high"; keepTemp=!!d.keepTemp; rememberProject=d.rememberForProject !== false
    }
    function pushDraft() {
        if (!controller) return false
        return controller.updateDraft({"presetId":selectedPresetId,"width":exportWidth,"height":exportHeight,"fps":exportFps,"quality":quality,"encoder":encoder,"subtitleMode":subtitleMode,"subtitleTrackId":subtitleTrackId,"outputFolder":outputFolder,"filename":filename,"overwritePolicy":overwritePolicy,"fitMode":fitMode,"audioEnabled":audioEnabled,"audioQuality":audioQuality,"keepTemp":keepTemp,"rememberForProject":rememberProject})
    }
    Component.onCompleted: loadDraft()
    Connections { target: root.controller; ignoreUnknownSignals:true; function onContextChanged(){ root.loadDraft() } }

    FolderDialog { id:folderDialog; title:"Choose Export Folder"; onAccepted:{ root.outputFolder=root.controller ? root.controller.localPathFromUrl(selectedFolder) : selectedFolder.toString(); settingsPanel.outputFolder=root.outputFolder; root.pushDraft() } }
    Dialog { id:presetDialog; modal:true; title:"Save Export Preset"; standardButtons:Dialog.NoButton; width:420
        ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
            AppTextField { id:presetName; Layout.fillWidth:true; placeholderText:"My Vertical HQ" }
            AppTextField { id:presetDescription; Layout.fillWidth:true; placeholderText:"Optional description" }
            RowLayout { Layout.fillWidth:true; Item{Layout.fillWidth:true}; SecondaryButton{text:"Cancel";onClicked:presetDialog.close()}; AppButton{text:"Save";onClicked:{root.pushDraft(); if(root.controller && root.controller.saveAsPreset(presetName.text,presetDescription.text)){presetDialog.close();presetName.text="";presetDescription.text=""}}} }
        }
    }

    ScrollView {
        anchors.fill:parent; clip:true
        ColumnLayout {
            width: root.width; spacing:Theme.spacing.lg
            RowLayout { Layout.fillWidth:true
                ColumnLayout { Layout.fillWidth:true; spacing:2
                    Text { text:"Export"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.titleLarge; font.weight:Theme.type.semibold }
                    Text { text:"Choose a platform preset, review settings, then export locally."; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
                }
                StatusBadge { text:"Local Export"; status:"ready" }
            }
            SectionHeader { title:"Choose Preset"; subtitle:"Presets are convenient app defaults, not immutable platform rules." }
            Flow {
                Layout.fillWidth:true; spacing:Theme.spacing.sm
                Repeater { model:root.controller ? root.controller.presets : []
                    delegate: ExportPresetCard { required property var modelData; preset:modelData; selected:root.selectedPresetId===modelData.id; onChosen:{if(root.controller && root.controller.selectPreset(modelData.id)){root.loadDraft()}}; onDuplicateRequested:root.controller.duplicatePreset(modelData.id); onDeleteRequested:root.controller.deletePreset(modelData.id) }
                }
            }
            ExportSettingsPanel {
                id:settingsPanel; Layout.fillWidth:true; controller:root.controller
                exportWidth:root.exportWidth; exportHeight:root.exportHeight; exportFps:root.exportFps; quality:root.quality; encoder:root.encoder; subtitleMode:root.subtitleMode; subtitleTrackId:root.subtitleTrackId; outputFolder:root.outputFolder; filename:root.filename; overwritePolicy:root.overwritePolicy; fitMode:root.fitMode; audioEnabled:root.audioEnabled; audioQuality:root.audioQuality; keepTemp:root.keepTemp; rememberProject:root.rememberProject
                onChanged:{root.exportWidth=exportWidth;root.exportHeight=exportHeight;root.exportFps=exportFps;root.quality=quality;root.encoder=encoder;root.subtitleMode=subtitleMode;root.subtitleTrackId=subtitleTrackId;root.outputFolder=outputFolder;root.filename=filename;root.overwritePolicy=overwritePolicy;root.fitMode=fitMode;root.audioEnabled=audioEnabled;root.audioQuality=audioQuality;root.keepTemp=keepTemp;root.rememberProject=rememberProject;root.pushDraft()}
                onBrowseRequested:folderDialog.open()
                onValidateRequested:{root.pushDraft();if(root.controller)root.controller.validateDraft()}
                onExportRequested:{if(root.pushDraft() && root.controller)root.controller.start()}
                onSavePresetRequested:presetDialog.open()
            }
            ExportSummary { Layout.fillWidth:true; controller:root.controller; visible:!root.controller || (!root.controller.busy && root.controller.stage!=="completed") }
            ExportProgress { Layout.fillWidth:true; controller:root.controller; visible:root.controller && root.controller.busy }
            ExportComplete { Layout.fillWidth:true; controller:root.controller; visible:root.controller && root.controller.stage==="completed" && root.controller.lastOutput.id; onAnotherVersionRequested:{root.controller.exportAgain(root.controller.lastOutput.id);root.loadDraft()} }
            ExportHistory { Layout.fillWidth:true; controller:root.controller }
            Item { Layout.preferredHeight:Theme.spacing.lg }
        }
    }
}
