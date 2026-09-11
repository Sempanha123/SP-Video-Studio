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
        Text { text:"3 · Translation"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
        RowLayout { Layout.fillWidth:true
            AppComboBox { id:translation; Layout.fillWidth:true; model:controller.translationOptions; textRole:"label" }
            AppButton { text:"Link Translation"; enabled:translation.currentIndex>=0; onClicked:controller.linkTranslation(translation.model[translation.currentIndex].id) }
            SecondaryButton { text:"Review"; onClicked:root.navigateRequested("translation") }
        }
        Text { text:controller.project.translationId ? "Dub segments use translated_text and preserve translation segment IDs/timing." : "Create/review a segment-based translation first."; color:Theme.colors.textSecondary }
    }
}
