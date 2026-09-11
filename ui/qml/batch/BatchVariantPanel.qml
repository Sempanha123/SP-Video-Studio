import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
Item { id:root; property var controller; property var config:({languages:[],platforms:[],aspectRatios:[],voices:[],seed:0}); signal nextRequested()
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        Text { text:"4. Variants"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.titleMedium; font.weight:Theme.type.semibold }
        TextField { id:languages; Layout.fillWidth:true; placeholderText:"Languages: en, km, th, vi" }
        TextField { id:platforms; Layout.fillWidth:true; placeholderText:"Platforms: tiktok, youtube_shorts, facebook_square" }
        TextField { id:aspects; Layout.fillWidth:true; placeholderText:"Aspect ratios: 9:16, 16:9, 1:1" }
        TextField { id:voices; Layout.fillWidth:true; placeholderText:"Voice IDs (optional, comma separated)" }
        SpinBox { id:seed; from:0; to:2147483647; value:26; editable:true }
        Text { Layout.fillWidth:true; wrapMode:Text.WordWrap; color:Theme.colors.textSecondary; text:"Collection rotation is deterministic. The same Batch input + seed keeps the same Asset assignments on retry." }
        Button { text:"Continue to Review"; onClicked:{ root.config={languages:languages.text.split(',').map(x=>x.trim()).filter(Boolean),platforms:platforms.text.split(',').map(x=>x.trim()).filter(Boolean),aspectRatios:aspects.text.split(',').map(x=>x.trim()).filter(Boolean),voices:voices.text.split(',').map(x=>x.trim()).filter(Boolean),seed:seed.value}; root.nextRequested() } }
        Item { Layout.fillHeight:true }
    }
}
