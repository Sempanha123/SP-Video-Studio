import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    required property var controller
    signal navigateRequested(string mode)
    implicitHeight: 140
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.sm
        Text { text:"4 · Target voice"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:voice; Layout.fillWidth:true; model:controller.voiceOptions; textRole:"label" }
            AppButton { text:"Use Voice"; enabled:voice.currentIndex>=0; onClicked:controller.setProjectVoice(voice.model[voice.currentIndex].id) }
            SecondaryButton { text:"Voice Studio"; onClicked:root.navigateRequested("voice") }
        }
        Text { text:controller.project.targetVoiceId ? "Voice selected. Per-segment overrides remain available in the model." : "Preset, designed, or authorized reference voices only; source speakers are never cloned automatically."; color:Theme.colors.textSecondary; wrapMode:Text.Wrap }
    }
}
