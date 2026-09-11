import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
RowLayout {
    property var controller
    Text { text:"Timeline"; color:Theme.colors.textPrimary; font.family:Theme.type.family; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }
    Text { text:controller ? controller.playheadText+" / "+controller.durationText : ""; color:Theme.colors.textSecondary; font.family:Theme.type.family; font.pixelSize:Theme.type.bodySmall }
    Item { Layout.fillWidth:true }
    Text { text:"Storyboard and Timeline share the same scene data"; color:Theme.colors.textMuted; font.family:Theme.type.family; font.pixelSize:Theme.type.caption }
}
