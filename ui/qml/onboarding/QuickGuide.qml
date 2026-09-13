import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppDialog {
    id: root
    width: Math.min(720, parent ? parent.width - 48 : 720)
    height: Math.min(620, parent ? parent.height - 48 : 620)
    header: null; footer: null
    contentItem: ColumnLayout {
        spacing: Theme.spacing.md
        RowLayout { Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: "Quick Guide"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.titleLarge; font.weight: Theme.type.semibold }
            IconButton { iconName: "close"; tooltip: "Close guide"; onClicked: root.close() }
        }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
            ColumnLayout { width: parent.width; spacing: Theme.spacing.sm
                Repeater { model: [
                    ["Create a project","Choose Create, pick Video, News, Story, Translate & Dub or Shorts, then name the project."],
                    ["Import media","Use Project Media for files used by the current project. Asset Library is reusable media across projects."],
                    ["Add voice","In Speech/TTS, choose a Speaker and Voice separately, then generate only the rows you need."],
                    ["Add subtitles","Create or edit subtitle cues manually; speech recognition is optional."],
                    ["Use Timeline","Video, voice, captions and graphics are arranged by time here. Ctrl+B splits at the playhead."],
                    ["Export video","Choose an export preset and output folder, then press Export Video. FFmpeg must be configured for rendering."]
                ]; delegate: AppCard { required property var modelData; Layout.fillWidth: true; implicitHeight: 84; ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; Text{text:modelData[0];color:Theme.colors.textPrimary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodyStrong;font.weight:Theme.type.semibold} Text{Layout.fillWidth:true;text:modelData[1];wrapMode:Text.WordWrap;color:Theme.colors.textSecondary;font.family:Theme.type.family;font.pixelSize:Theme.type.bodySmall} } } }
            }
        }
    }
}
