import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { id:root; property var controller; property var config:({languages:[],platforms:[],aspectRatios:[],voices:[],seed:0}); signal nextRequested()
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        Text { text:"4. Variants"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleMedium; font.weight:Theme.type.semibold }
        AppTextField { id:languages; Layout.fillWidth:true; accessibleName:"Languages"; placeholderText:"Languages: en, km, th, vi" }
        AppTextField { id:platforms; Layout.fillWidth:true; accessibleName:"Platforms"; placeholderText:"Platforms: tiktok, youtube_shorts, facebook_square" }
        AppTextField { id:aspects; Layout.fillWidth:true; accessibleName:"Aspect ratios"; placeholderText:"Aspect ratios: 9:16, 16:9, 1:1" }
        AppTextField { id:voices; Layout.fillWidth:true; accessibleName:"Voice IDs"; placeholderText:"Voice IDs (optional, comma separated)" }
        SpinBox { id:seed; Accessible.name:"Deterministic batch seed"; Accessible.role:Accessible.SpinBox; from:0; to:2147483647; value:26; editable:true }
        Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; color:Theme.colors.textSecondary; text:"Collection rotation is deterministic. The same Batch input + seed keeps the same Asset assignments on retry." }
        AppButton { text:"Continue to Review"; onClicked:{ root.config={languages:languages.text.split(',').map(x=>x.trim()).filter(Boolean),platforms:platforms.text.split(',').map(x=>x.trim()).filter(Boolean),aspectRatios:aspects.text.split(',').map(x=>x.trim()).filter(Boolean),voices:voices.text.split(',').map(x=>x.trim()).filter(Boolean),seed:seed.value}; root.nextRequested() } }
        Item { Layout.fillHeight:true }
    }
}
