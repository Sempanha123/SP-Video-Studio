import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id: root
    property var controller
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
    signal browseRequested()
    signal changed()
    signal validateRequested()
    signal exportRequested()
    signal savePresetRequested()

    function encoderRows() { return controller ? controller.encoderOptions : [{"id":"auto","name":"Auto"}] }
    function subtitleRows() {
        var out=[{"id":"","name":"None"}]
        if (!controller) return out
        for (var i=0;i<controller.subtitleTracks.length;++i) out.push(controller.subtitleTracks[i])
        return out
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.spacing.lg; spacing: Theme.spacing.md
        SectionHeader { title: "Export Settings"; subtitle: "Simple defaults with advanced control when you need it" }
        GridLayout {
            Layout.fillWidth: true; columns: width < 650 ? 1 : 2; columnSpacing: Theme.spacing.md; rowSpacing: Theme.spacing.sm
            ColumnLayout { Layout.fillWidth: true
                Text { text: "Resolution"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                RowLayout { Layout.fillWidth: true
                    AppTextField { Layout.fillWidth: true; text: String(root.exportWidth); validator: IntValidator { bottom: 16; top: 7680 }; onEditingFinished: { root.exportWidth=Number(text); root.changed() } }
                    Text { text: "×"; color: Theme.colors.textMuted }
                    AppTextField { Layout.fillWidth: true; text: String(root.exportHeight); validator: IntValidator { bottom: 16; top: 7680 }; onEditingFinished: { root.exportHeight=Number(text); root.changed() } }
                }
            }
            ColumnLayout { Layout.fillWidth: true
                Text { text: "FPS"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: [24,25,30,50,60]; Component.onCompleted: currentIndex=Math.max(0,model.indexOf(root.exportFps)); onActivated: { root.exportFps=Number(currentText); root.changed() } }
            }
            ColumnLayout { Layout.fillWidth: true
                Text { text: "Quality"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: [{"id":"fast","name":"Fast"},{"id":"balanced","name":"Balanced"},{"id":"high","name":"High Quality"}]; textRole:"name"; valueRole:"id"; currentIndex: root.quality==="fast"?0:(root.quality==="high"?2:1); onActivated: { root.quality=currentValue; root.changed() } }
            }
            ColumnLayout { Layout.fillWidth: true
                Text { text: "Encoder"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: root.encoderRows(); textRole:"name"; valueRole:"id"; onActivated: { root.encoder=currentValue || "auto"; root.changed() } }
            }
            ColumnLayout { Layout.fillWidth: true
                Text { text: "Subtitle Behavior"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: [{"id":"none","name":"None"},{"id":"burn","name":"Burn Into Video"},{"id":"external_srt","name":"Export SRT Beside Video"},{"id":"external_vtt","name":"Export VTT Beside Video"},{"id":"external_ass","name":"Export ASS Beside Video"}]; textRole:"name"; valueRole:"id"; onActivated: { root.subtitleMode=currentValue; root.changed() } }
            }
            ColumnLayout { Layout.fillWidth: true; visible: root.subtitleMode !== "none"
                Text { text: "Subtitle Track"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: root.subtitleRows(); textRole:"name"; valueRole:"id"; onActivated: { root.subtitleTrackId=currentValue || ""; root.changed() } }
            }
            ColumnLayout { Layout.fillWidth: true
                Text { text: "Aspect Conversion"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: [{"id":"fit","name":"Fit"},{"id":"fill","name":"Fill"},{"id":"stretch","name":"Stretch"}]; textRole:"name"; valueRole:"id"; currentIndex: root.fitMode==="fit"?0:(root.fitMode==="stretch"?2:1); onActivated: { root.fitMode=currentValue; root.changed() } }
            }
            ColumnLayout { Layout.fillWidth: true
                Text { text: "If File Exists"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                AppComboBox { Layout.fillWidth: true; model: [{"id":"keep_both","name":"Keep Both"},{"id":"replace","name":"Replace"},{"id":"cancel","name":"Cancel"}]; textRole:"name"; valueRole:"id"; currentIndex: root.overwritePolicy==="replace"?1:(root.overwritePolicy==="cancel"?2:0); onActivated: { root.overwritePolicy=currentValue; root.changed() } }
            }
        }
        ColumnLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
            Text { text: "Output Folder"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            RowLayout { Layout.fillWidth: true
                AppTextField { Layout.fillWidth: true; text: root.outputFolder; onEditingFinished: { root.outputFolder=text; root.changed() } }
                SecondaryButton { text: "Browse"; compact: true; onClicked: root.browseRequested() }
            }
        }
        ColumnLayout { Layout.fillWidth: true; spacing: Theme.spacing.xs
            Text { text: "Filename"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
            AppTextField { Layout.fillWidth: true; text: root.filename; onEditingFinished: { root.filename=text; root.changed() } }
        }
        RowLayout { Layout.fillWidth: true
            AppSwitch { checked: root.audioEnabled; onToggled: { root.audioEnabled=checked; root.changed() } }
            Text { text: "Audio"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall }
            AppComboBox { enabled: root.audioEnabled; model: [{"id":"standard","name":"Standard"},{"id":"high","name":"High"}]; textRole:"name"; valueRole:"id"; currentIndex: root.audioQuality==="standard"?0:1; onActivated: { root.audioQuality=currentValue; root.changed() } }
            Item { Layout.fillWidth: true }
            AppSwitch { checked: root.rememberProject; onToggled: { root.rememberProject=checked; root.changed() } }
            Text { text: "Remember for this project"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
        }
        RowLayout { Layout.fillWidth: true
            SecondaryButton { text: "Save as Preset"; compact: true; onClicked: root.savePresetRequested() }
            SecondaryButton { text: "Validate"; compact: true; onClicked: root.validateRequested() }
            Item { Layout.fillWidth: true }
            AppButton { text: "Export Video"; iconName: "export"; compact: true; onClicked: root.exportRequested() }
        }
    }
}
