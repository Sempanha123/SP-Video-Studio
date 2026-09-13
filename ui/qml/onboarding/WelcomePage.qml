import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

SetupStep {
    title: "Welcome to MMO Video Studio"
    description: "Create, dub, edit and produce videos faster. Setup is short, optional, and you can change everything later."
    GridLayout {
        Layout.fillWidth: true
        columns: width < 650 ? 1 : 2
        columnSpacing: Theme.spacing.md
        rowSpacing: Theme.spacing.md
        Repeater {
            model: [
                ["Video Editing","Import media and edit manually."],
                ["News","Build source-grounded news with reporter, B-roll and captions."],
                ["Story","Plan scenes, narration and music."],
                ["Translate & Dub","Transcribe, translate and dub existing video."],
                ["Shorts","Create vertical short-form edits."],
                ["Voice & Batch","Generate selected speech or produce template-based variations later."]
            ]
            delegate: AppCard {
                required property var modelData
                Layout.fillWidth: true; implicitHeight: 86
                ColumnLayout { anchors.fill: parent; anchors.margins: Theme.spacing.md; spacing: 3
                    Text { text: modelData[0]; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodyStrong; font.weight: Theme.type.semibold }
                    Text { Layout.fillWidth: true; text: modelData[1]; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.bodySmall; wrapMode: Text.WordWrap }
                }
            }
        }
    }
    InfoBanner { Layout.fillWidth: true; text: "AI is optional. Manual editing, project setup and normal Timeline work remain available without AI models or internet." }
}
