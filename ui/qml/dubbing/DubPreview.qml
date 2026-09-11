import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
AppCard {
    id: root
    required property var controller
    implicitHeight:120
    RowLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg
        ColumnLayout { Layout.fillWidth:true
            Text { text:"7 · Preview"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
            Text { text:"Preview Original, Dub Only, or Mixed using the existing Playback service. Rebuild only when audio inputs change."; color:Theme.colors.textSecondary; wrapMode:Text.Wrap; Layout.fillWidth:true }
        }
        SecondaryButton { text:"Original"; onClicked:controller.requestPreview("original") }
        SecondaryButton { text:"Dub Only"; onClicked:controller.requestPreview("dub") }
        AppButton { text:"Mixed"; onClicked:controller.requestPreview("mixed") }
    }
}
